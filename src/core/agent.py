"""Agent ReAct 循环 —— 把 LLM 和工具串起来"""

import json
from src.core.llm import LLM
from src.core.tool import ToolRegistry
from src.core.memory import ConversationMemory
from src.core.context import build_system_prompt  # Hermes 风格：外置系统提示词


class Agent:
    """ReAct Agent：思考 -> 行动 -> 观察 循环"""

    def __init__(self, llm: LLM, tool_registry: ToolRegistry,
                 system_prompt: str = None, vector_memory=None):
        self.llm = llm
        self.tools = tool_registry
        # 优先使用传入的 system_prompt，否则从 SOUL.md + CONTEXT.md 加载
        self.system_prompt = system_prompt or build_system_prompt()
        self.memory = ConversationMemory()
        self.memory.set_system(self.system_prompt)
        self.vector_memory = vector_memory
        self._recent_tool_calls: list = []  # 重复检测滑动窗口
        # 统计计数器
        self.stats = {"tool_calls": 0, "steps": 0, "total_tokens": 0}  # 运行统计

    def run(self, user_input: str, max_steps: int = 10,
            auto_recall: bool = True, auto_remember: bool = False) -> str:
        """执行一次 Agent 对话（ReAct 循环核心）

        Args:
            user_input: 用户输入
            max_steps: 最大循环步数，防止死循环
            auto_recall: 是否自动检索长期记忆
            auto_remember: 是否自动存储对话到长期记忆
        Returns:
            Agent 的最终回复
        """
        # 自动检索长期记忆并注入上下文
        recalled_context = self._get_recalled_context(user_input) if auto_recall and self.vector_memory else ""

        user_message = {"role": "user", "content": user_input}
        if recalled_context:
            user_message["content"] = f"{recalled_context}\n## 当前问题\n{user_input}"

        self.memory.add_message(user_message)  # 添加用户消息到记忆
        tools_openai = self.tools.to_openai_format()  # 工具定义（每轮相同，可缓存但暂不优化）
        self._recent_tool_calls = []  # 重置重复检测滑动窗口

        for step in range(max_steps):
            self.stats["steps"] = step + 1  # 记录步数
            message = self.llm.chat_with_tools(self.memory.to_messages(), tools_openai)

            if message.tool_calls:
                # 检测重复调用（连续 2 次相同则终止）
                current_calls = tuple(tc.function.name for tc in message.tool_calls)
                self._recent_tool_calls.append(current_calls)
                if len(self._recent_tool_calls) > 2:
                    self._recent_tool_calls.pop(0)  # 保持窗口大小 2
                if len(self._recent_tool_calls) >= 2 and len(set(self._recent_tool_calls)) == 1:
                    return f"检测到重复调用 {', '.join(current_calls)}，已终止。请换一种方式重试。"

                # 记录助手消息（含 tool_calls）
                self.memory.add_message({
                    "role": "assistant", "content": message.content,
                    "tool_calls": [
                        {"id": tc.id, "type": "function", "function": {
                            "name": tc.function.name, "arguments": tc.function.arguments,
                        }}
                        for tc in message.tool_calls
                    ]
                })

                # 执行每个工具调用并记录结果
                for tc in message.tool_calls:
                    self.stats["tool_calls"] += 1  # 统计
                    result = self._safe_execute_tool(tc.function.name, tc.function.arguments)
                    self.memory.add_message({"role": "tool", "tool_call_id": tc.id, "content": result})
            else:
                # LLM 返回文本 → 对话结束
                self.memory.add_message({"role": "assistant", "content": message.content})
                final_answer = message.content or ""

                # 可选自动存储到长期记忆
                if auto_remember and self.vector_memory and final_answer:
                    try:
                        self.vector_memory.remember(
                            f"conv_{abs(hash(user_input)):08x}",
                            f"Q: {user_input}\nA: {final_answer[:300]}"
                        )
                    except Exception:
                        pass
                return final_answer

        return "Agent 执行超过最大步数，任务中断。"

    def _get_recalled_context(self, query: str) -> str:
        """检索长期记忆并格式化为上下文文本"""
        try:
            recalled = self.vector_memory.recall(query, n_results=2)
            return "\n".join([f"- {r['content']}" for r in recalled]) if recalled else ""
        except Exception:
            return ""  # 向量记忆不可用时静默跳过

    def reset_memory(self):
        """清除短期对话记忆"""
        self.memory.reset()
        self._recent_tool_calls = []
        self.stats = {"tool_calls": 0, "steps": 0, "total_tokens": 0}  # 重置统计

    def _safe_execute_tool(self, name: str, args_str: str) -> str:
        """安全执行工具：JSON 解析兜底 + 错误友好返回"""
        import ast
        # 1. 尝试 JSON 解析，失败用 ast.literal_eval 兜底
        try:
            args = json.loads(args_str)
        except (json.JSONDecodeError, TypeError):
            try:
                # 尝试修复常见 LLM 输出格式问题
                cleaned = args_str.strip().replace("'", '"')
                args = json.loads(cleaned)
            except (json.JSONDecodeError, TypeError):
                return f"错误：工具参数解析失败，请检查 JSON 格式: {args_str[:100]}"
        # 2. 执行工具
        return self.tools.execute(name, args)

    def compress_history(self) -> str:
        """压缩对话历史：用 LLM 生成摘要替换原始消息（Hermes /compress 风格）"""
        messages = self.memory.to_messages()
        if len(messages) < 4:
            return "消息太少，无需压缩"
        # 用 LLM 生成摘要
        summary = self.llm.chat(
            [{"role": "user", "content": f"请用中文简短总结以下对话的关键信息（200字内）：\n{str(messages)}"}],
            temperature=0.0
        )
        self.memory.reset()
        self.memory.add_message({"role": "user", "content": f"[历史摘要] {summary}"})
        return summary

    def run_planned(self, task: str, planner, verbose: bool = False) -> str:
        """拆解任务 → 逐步执行 → 汇总结果"""
        steps = planner.decompose(task)
        if len(steps) <= 1:
            return self.run(task)  # 单步或分解失败直接执行

        results = [
            f"Step {i}: {step}\n结果: {self.run(step)}"
            for i, step in enumerate(steps, 1)
        ]
        return "任务执行完毕：\n\n" + "\n\n".join(results)
