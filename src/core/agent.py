"""Agent ReAct 循环 —— LLM + 工具（Hermes 协议对齐：结构化输出 + 流式 + 回调）"""

import json
from src.core.llm import LLM
from src.core.tool import ToolRegistry
from src.core.memory import ConversationMemory
from src.core.context import build_system_prompt
from src.core.protocol import AgentResult, StopReason, StreamEvent, StreamChunk, DEFAULT_CALLBACKS


class Agent:
    """ReAct Agent：思考 -> 行动 -> 观察 循环"""

    def __init__(self, llm: LLM, tool_registry: ToolRegistry,
                 system_prompt: str = None, vector_memory=None, callbacks: dict = None):
        self.llm = llm  # LLM 客户端
        self.tools = tool_registry  # 工具注册表
        self.system_prompt = system_prompt or build_system_prompt()  # SOUL.md + CONTEXT.md
        self.memory = ConversationMemory()  # 短期对话记忆
        self.memory.set_system(self.system_prompt)
        self.vector_memory = vector_memory  # 长期记忆
        self._recent_tool_calls: list = []  # 重复检测
        self.stats = {"tool_calls": 0, "steps": 0, "total_tokens": 0}  # 运行统计
        self.callbacks = DEFAULT_CALLBACKS | (callbacks or {})  # Hermes 风格回调
        # Phase 4: 技能模式跟踪（3 次相同序列自动建议）
        self._tool_seq: list[tuple] = []  # k-最近工具调用序列
        self._auto_consolidate: bool = True  # Phase 3: 自动巩固记忆

    # === Hermes 对齐：3 种入口 ===

    def chat(self, user_input: str) -> str:
        """简洁入口：返回最终回复文本"""
        return self.run(user_input, return_result=False)

    def run_conversation(self, user_input: str) -> AgentResult:
        """完整入口：返回结构化 AgentResult"""
        return self.run(user_input, return_result=True)

    def run(self, user_input: str, max_steps: int = 10,
            auto_recall: bool = True, auto_remember: bool = False,
            return_result: bool = False):
        """执行一次对话（向后兼容）

        Args:
            user_input: 用户输入
            max_steps: 最大步数
            return_result: True=AgentResult, False=str（兼容旧调用）
        """
        recalled_context = self._get_recalled_context(user_input) if auto_recall and self.vector_memory else ""
        user_message = {"role": "user", "content": user_input}
        if recalled_context:
            user_message["content"] = f"{recalled_context}\n## 当前问题\n{user_input}"
        self.memory.add_message(user_message)
        tools_openai = self.tools.to_openai_format()
        self._recent_tool_calls = []
        self.stats = {"tool_calls": 0, "steps": 0, "total_tokens": 0}
        stop_reason = StopReason.COMPLETE

        for step in range(max_steps):
            self.stats["steps"] = step + 1
            self.callbacks["on_step"]({"step": step + 1})
            message = self.llm.chat_with_tools(self.memory.to_messages(), tools_openai)
            if message.tool_calls:
                current_calls = tuple(f"{tc.function.name}:{tc.function.arguments}" for tc in message.tool_calls)
                self._recent_tool_calls.append(current_calls)
                if len(self._recent_tool_calls) > 2:
                    self._recent_tool_calls.pop(0)
                if len(self._recent_tool_calls) >= 2 and len(set(self._recent_tool_calls)) == 1:
                    stop_reason = StopReason.DUPLICATE
                    msg = f"检测到重复调用 {', '.join(tc.function.name for tc in message.tool_calls)}，已终止"
                    self._finalize_memory(assistant_msg={"role": "assistant", "content": msg})
                    break
                self.memory.add_message({
                    "role": "assistant", "content": message.content,
                    "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in message.tool_calls]
                })
                for tc in message.tool_calls:
                    self.stats["tool_calls"] += 1
                    self.callbacks["on_tool_call"]({"name": tc.function.name, "arguments": tc.function.arguments})
                    result = self._safe_execute_tool(tc.function.name, tc.function.arguments)
                    self.callbacks["on_tool_result"]({"name": tc.function.name, "result": result})
                    self.memory.add_message({"role": "tool", "tool_call_id": tc.id, "content": result})
            else:
                self.memory.add_message({"role": "assistant", "content": message.content})
                final_answer = message.content or ""
                if auto_remember and self.vector_memory and final_answer:
                    try:
                        self.vector_memory.remember(f"conv_{abs(hash(user_input)):08x}", f"Q: {user_input}\nA: {final_answer[:300]}")
                    except Exception: pass
                # Phase 3: 复杂任务自动巩固记忆
                if self._auto_consolidate and self.stats["tool_calls"] >= 3 and self.vector_memory:
                    try:
                        self.vector_memory.remember(f"task_{abs(hash(user_input)):08x}", f"任务: {user_input}\n工具调用: {self.stats['tool_calls']}次\n结果: {final_answer[:200]}")
                    except Exception: pass
                result = AgentResult(final_response=final_answer, messages=self.memory.to_messages(), stats=self.stats, stop_reason=stop_reason)
                self.callbacks["on_complete"]({"result": result})
                return result if return_result else final_answer

        result = AgentResult(final_response="Agent 执行超过最大步数", messages=self.memory.to_messages(), stats=self.stats, stop_reason=StopReason.MAX_STEPS)
        self.callbacks["on_complete"]({"result": result})
        return result if return_result else result.final_response

    def _finalize_memory(self, assistant_msg: dict):
        self.memory.add_message(assistant_msg)

    # === 流式执行 ===
    def run_stream(self, user_input: str, max_steps: int = 10):
        """流式执行——逐 token yield（Hermes stream_delta_callback 对齐）"""
        recalled_context = self._get_recalled_context(user_input) if self.vector_memory else ""
        text = f"{recalled_context}\n## 当前问题\n{user_input}" if recalled_context else user_input
        self.memory.add_message({"role": "user", "content": text})
        tools_openai = self.tools.to_openai_format()
        self._recent_tool_calls = []

        for step in range(max_steps):
            self.stats["steps"] = step + 1
            yield StreamChunk(StreamEvent.STEP_START, {"step": step + 1})
            final_message = None
            for event in self.llm.chat_stream(self.memory.to_messages(), tools_openai):
                if event["type"] == "token":
                    yield StreamChunk(StreamEvent.TOKEN, {"step": step + 1, "token": event["content"]})
                elif event["type"] == "done":
                    final_message = event["message"]
            if not final_message: break
            message = final_message
            if message.tool_calls:
                current_calls = tuple(f"{tc.function.name}:{tc.function.arguments}" for tc in message.tool_calls)
                self._recent_tool_calls.append(current_calls)
                if len(self._recent_tool_calls) > 2: self._recent_tool_calls.pop(0)
                if len(self._recent_tool_calls) >= 2 and len(set(self._recent_tool_calls)) == 1:
                    yield StreamChunk(StreamEvent.COMPLETE, {"stop_reason": "duplicate"})
                    return
                self.memory.add_message({
                    "role": "assistant", "content": message.content,
                    "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in message.tool_calls]
                })
                for tc in message.tool_calls:
                    self.stats["tool_calls"] += 1
                    yield StreamChunk(StreamEvent.TOOL_CALL, {"name": tc.function.name, "arguments": tc.function.arguments})
                    result = self._safe_execute_tool(tc.function.name, tc.function.arguments)
                    yield StreamChunk(StreamEvent.TOOL_RESULT, {"name": tc.function.name, "result": result})
                    self.memory.add_message({"role": "tool", "tool_call_id": tc.id, "content": result})
            else:
                self.memory.add_message({"role": "assistant", "content": message.content})
                result = AgentResult(final_response=message.content or "", messages=self.memory.to_messages(), stats=self.stats, stop_reason=StopReason.COMPLETE)
                yield StreamChunk(StreamEvent.COMPLETE, {"result": result.to_dict()})
                return
        yield StreamChunk(StreamEvent.COMPLETE, {"stop_reason": "max_steps"})

    # === 辅助方法 ===
    def _safe_execute_tool(self, name: str, args_str: str) -> str:
        """安全执行工具：JSON 解析兜底"""
        try:
            args = json.loads(args_str)
        except (json.JSONDecodeError, TypeError):
            try:
                args = json.loads(args_str.strip().replace("'", '"'))
            except (json.JSONDecodeError, TypeError):
                return f"错误：参数解析失败: {args_str[:100]}"
        return self.tools.execute(name, args)

    def _get_recalled_context(self, query: str) -> str:
        """检索长期记忆并格式化为上下文"""
        try: return "\n".join(f"- {r['content']}" for r in self.vector_memory.recall(query, n_results=2))
        except Exception: return ""

    def reset_memory(self):
        self.memory.reset()
        self._recent_tool_calls = []
        self._tool_seq = []
        self.stats = {"tool_calls": 0, "steps": 0, "total_tokens": 0}

    def compress_history(self) -> str:
        """压缩对话历史：LLM 生成摘要"""
        messages = self.memory.to_messages()
        if len(messages) < 4: return "消息太少，无需压缩"
        summary = self.llm.chat([{"role": "user", "content": f"请用中文简短总结（200字内）：\n{str(messages)}"}], temperature=0.0)
        self.memory.reset()
        self.memory.add_message({"role": "user", "content": f"[历史摘要] {summary}"})
        return summary

    def run_planned(self, task: str, planner, verbose: bool = False) -> str:
        steps = planner.decompose(task)
        if len(steps) <= 1: return self.run(task, return_result=False)
        return "任务执行完毕：\n\n" + "\n\n".join(f"Step {i}: {step}\n结果: {self.run(step, return_result=False)}" for i, step in enumerate(steps, 1))
