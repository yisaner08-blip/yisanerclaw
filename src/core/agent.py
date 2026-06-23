"""Agent ReAct 循环 —— 把 LLM 和工具串起来"""

import json
from src.core.llm import LLM
from src.core.tool import ToolRegistry
from src.core.memory import ConversationMemory


class Agent:
    def __init__(self, llm: LLM, tool_registry: ToolRegistry,
                 system_prompt: str = None, vector_memory=None):
        self.llm = llm
        self.tools = tool_registry
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.memory = ConversationMemory()
        self.memory.set_system(self.system_prompt)
        self.vector_memory = vector_memory  # 可选长期记忆
        self._recent_tool_calls: list[str] = []  # 重复检测

    def _default_system_prompt(self) -> str:
        return (
            "你是智能助手，可使用工具完成任务。\n\n"
            "<rules>\n"
            "- 已知道答案时直接回答，不要调用工具\n"
            "- 需要最新/外部信息时用 web_search 或 web_fetch\n"
            "- 需要文件操作时用 read_file/write_file/list_directory\n"
            "- 需要执行命令时用 run_shell\n"
            "- 数学计算用 calculator\n"
            "- 工具返回错误时，分析原因后修正参数重试（最多1次）\n"
            "- 回答简洁准确，优先用列表，避免冗长\n"
            "- 你的知识截止 2025年5月，之后的事件请用搜索工具\n"
            "</rules>"
        )

    def run(self, user_input: str, max_steps: int = 10,
            auto_recall: bool = True, auto_remember: bool = False) -> str:
        # 自动检索长期记忆
        recalled_context = ""
        if auto_recall and self.vector_memory:
            try:
                recalled = self.vector_memory.recall(user_input, n_results=2)
                if recalled:
                    recalled_context = "## 相关历史记忆\n"
                    for r in recalled:
                        recalled_context += f"- {r['content']}\n"
            except Exception:
                pass  # vector_memory 不可用时静默跳过

        user_message = {"role": "user", "content": user_input}
        if recalled_context:
            user_message["content"] = f"{recalled_context}\n## 当前问题\n{user_input}"

        self.memory.add_message(user_message)
        tools_openai = self.tools.to_openai_format()
        self._recent_tool_calls = []
        last_tool_call = None

        for step in range(max_steps):
            messages = self.memory.to_messages()
            message = self.llm.chat_with_tools(messages, tools_openai)

            if message.tool_calls:
                # 重复检测：最近 2 次调用相同则终止
                current_calls = tuple(tc.function.name for tc in message.tool_calls)
                self._recent_tool_calls.append(current_calls)
                if len(self._recent_tool_calls) > 2:
                    self._recent_tool_calls.pop(0)
                if len(self._recent_tool_calls) >= 2 and len(set(self._recent_tool_calls)) == 1:
                    names = ", ".join(current_calls)
                    return f"检测到重复调用 {names}，已终止。请换一种方式重试。"

                self.memory.add_message({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id, "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })

                for tc in message.tool_calls:
                    tool_name = tc.function.name
                    tool_args = json.loads(tc.function.arguments)
                    result = self.tools.execute(tool_name, tool_args)
                    last_tool_call = (tool_name, tool_args, result)
                    self.memory.add_message({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
            else:
                self.memory.add_message({"role": "assistant", "content": message.content})

                # 自动记住重要信息
                final_answer = message.content or ""
                if auto_remember and self.vector_memory and final_answer:
                    try:
                        self.vector_memory.remember(
                            f"conv_{id(self)}_{hash(user_input) & 0x7FFFFFFF:08x}",
                            f"Q: {user_input}\nA: {final_answer[:300]}"
                        )
                    except Exception:
                        pass

                return final_answer

        return "Agent 执行超过最大步数，任务中断。"

    def reset_memory(self):
        """清除对话记忆，开始新对话"""
        self.memory.reset()
        self._recent_tool_calls = []

    def run_planned(self, task: str, planner, verbose: bool = False) -> str:
        """拆解任务 → 逐步执行 → 汇总结果"""
        steps = planner.decompose(task)
        if not steps:
            return self.run(task)

        results = []
        for i, step in enumerate(steps, 1):
            if verbose:
                print(f"\n[Step {i}/{len(steps)}] {step}")
            result = self.run(step)
            results.append(f"Step {i}: {step}\n结果: {result}")

        if len(results) == 1:
            return results[0]
        return "任务执行完毕：\n\n" + "\n\n".join(results)
