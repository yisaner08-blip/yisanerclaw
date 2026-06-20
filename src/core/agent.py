"""Agent ReAct 循环 —— 把 LLM 和工具串起来"""

import json
from src.core.llm import LLM
from src.core.tool import ToolRegistry
from src.core.memory import ConversationMemory


class Agent:
    def __init__(self, llm: LLM, tool_registry: ToolRegistry, system_prompt: str = None):
        self.llm = llm
        self.tools = tool_registry
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.memory = ConversationMemory()
        self.memory.set_system(self.system_prompt)

    def _default_system_prompt(self) -> str:
        return (
            "你是一个智能助手，可以使用工具来完成任务。"
            "当需要获取信息或执行操作时，请使用合适的工具。"
            "当你已经完成任务时，直接给出最终答案，不要再调用工具。"
        )

    def run(self, user_input: str, max_steps: int = 10) -> str:
        self.memory.add_message({"role": "user", "content": user_input})
        tools_openai = self.tools.to_openai_format()

        for _ in range(max_steps):
            messages = self.memory.to_messages()
            message = self.llm.chat_with_tools(messages, tools_openai)

            if message.tool_calls:
                # 追加助手消息（含 tool_calls）
                self.memory.add_message({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })
                # 执行工具并追加结果
                for tc in message.tool_calls:
                    tool_name = tc.function.name
                    tool_args = json.loads(tc.function.arguments)
                    result = self.tools.execute(tool_name, tool_args)
                    self.memory.add_message({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
            else:
                self.memory.add_message({"role": "assistant", "content": message.content})
                return message.content or ""

        return "Agent 执行超过最大步数，任务中断。"

    def reset_memory(self):
        """清除对话记忆，开始新对话"""
        self.memory.reset()

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
