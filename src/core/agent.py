"""Agent ReAct 循环 —— 把 LLM 和工具串起来"""

import json
from src.core.llm import LLM
from src.core.tool import ToolRegistry
from src.core.memory import ConversationMemory


class Agent:
    """ReAct Agent：思考 -> 行动 -> 观察 循环"""

    def __init__(self, llm: LLM, tool_registry: ToolRegistry,
                 system_prompt: str = None, vector_memory=None):
        """初始化 Agent

        Args:
            llm: 大模型客户端
            tool_registry: 工具注册表
            system_prompt: 系统提示词，默认使用内置规则
            vector_memory: 可选长期向量记忆
        """
        self.llm = llm  # LLM 客户端
        self.tools = tool_registry  # 工具注册表
        self.system_prompt = system_prompt or self._default_system_prompt()  # 系统提示词
        self.memory = ConversationMemory()  # 短期对话记忆
        self.memory.set_system(self.system_prompt)
        self.vector_memory = vector_memory  # 可选长期记忆
        self._recent_tool_calls: list = []  # 滑动窗口记录最近调用，用于重复检测

    def _default_system_prompt(self) -> str:
        """内置系统提示词：工具选择策略 + 行为约束"""
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

        for _ in range(max_steps):
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
                    result = self.tools.execute(tc.function.name, json.loads(tc.function.arguments))
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
