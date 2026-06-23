"""记忆模块 —— 短期对话记忆（Token 感知滑动窗口）"""


def _estimate_tokens(text: str) -> int:
    """快速估算 token 数：中文 ~1.5 字/token，英文 ~4 字/token"""
    return max(1, len(text) // 2)


class ConversationMemory:
    def __init__(self, max_turns: int = 20, max_tokens: int = 16000):
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.system_message: dict | None = None
        self.messages: list[dict] = []

    def set_system(self, content: str):
        self.system_message = {"role": "system", "content": content}

    def add_message(self, message: dict):
        self.messages.append(message)

    def _total_tokens(self, messages: list[dict]) -> int:
        return sum(_estimate_tokens(str(m.get("content", ""))) for m in messages)

    def to_messages(self) -> list[dict]:
        result = []
        if self.system_message:
            result.append(self.system_message)

        # 按数量窗口裁剪
        recent = self.messages[-self.max_turns * 4:]
        result.extend(recent)

        # 按 token 量裁剪（保留 system + 最新消息）
        if self.max_tokens > 0:
            while self._total_tokens(result) > self.max_tokens and len(result) > 2:
                del result[2]  # 跳过 system(0) 和最旧 user(1)，删除更旧消息

        return result

    def reset(self):
        self.messages = []
