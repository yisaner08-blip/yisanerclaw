"""记忆模块 —— 短期对话记忆（Token 感知滑动窗口）"""


def _estimate_tokens(text: str) -> int:
    """快速估算 token 数：取字符数的一半作为粗略估计"""
    return max(1, len(text) // 2)


class ConversationMemory:
    """短期对话记忆：滑动窗口 + Token 限制双保险"""

    def __init__(self, max_turns: int = 20, max_tokens: int = 16000):
        """
        Args:
            max_turns: 最大保留轮数（每轮约 4 条消息）
            max_tokens: Token 上限，超量时裁剪旧消息（0 表示不限制）
        """
        self.max_turns = max_turns  # 消息数量窗口
        self.max_tokens = max_tokens  # Token 上限
        self.system_message: dict | None = None  # 系统提示词（永不裁剪）
        self.messages: list[dict] = []  # 对话历史

    def set_system(self, content: str):
        """设置系统提示词，始终保留在窗口顶部"""
        self.system_message = {"role": "system", "content": content}

    def add_message(self, message: dict):
        """追加一条消息到历史"""
        self.messages.append(message)

    def _total_tokens(self, messages: list[dict]) -> int:
        """估算消息列表的总 token 数"""
        return sum(_estimate_tokens(str(m.get("content", ""))) for m in messages)

    def to_messages(self) -> list[dict]:
        """构建当前消息列表（已应用滑动窗口 + Token 裁剪）"""
        result = [self.system_message] if self.system_message else []  # system 始终保留
        result.extend(self.messages[-self.max_turns * 4:])  # 按消息数滑动窗口

        # Token 超量时从旧消息开始裁剪（跳过 system 和首条 user）
        if self.max_tokens > 0:
            while self._total_tokens(result) > self.max_tokens and len(result) > 2:
                del result[2]

        return result

    def reset(self):
        """清空对话历史，保留 system 提示词"""
        self.messages = []
