"""记忆模块 —— 短期对话记忆（滑动窗口）"""


class ConversationMemory:
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.system_message: dict | None = None
        self.messages: list[dict] = []

    def set_system(self, content: str):
        self.system_message = {"role": "system", "content": content}

    def add_message(self, message: dict):
        self.messages.append(message)

    def to_messages(self) -> list[dict]:
        result = []
        if self.system_message:
            result.append(self.system_message)
        result.extend(self.messages[-self.max_turns * 4:])
        return result

    def reset(self):
        self.messages = []
