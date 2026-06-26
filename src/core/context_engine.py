"""上下文引擎 —— Hermes 对齐：可插拔策略（ponytail: stdlib abc）"""

from abc import ABC, abstractmethod
from src.core.llm import LLM


class ContextEngine(ABC):
    """上下文管理抽象基类"""

    @abstractmethod
    def add_message(self, role: str, content: str):
        """添加消息"""

    @abstractmethod
    def to_messages(self) -> list[dict]:
        """构建消息列表"""

    @abstractmethod
    def compress(self, llm: LLM) -> str:
        """压缩上下文"""

    @abstractmethod
    def reset(self):
        """重置上下文"""


class SlidingWindowEngine(ContextEngine):
    """滑动窗口策略（默认）：保留最近 N 条消息"""
    def __init__(self, window_size: int = 80):
        self.window = window_size  # 窗口大小
        self.messages: list[dict] = []

    def add_message(self, role: str, content: str): self.messages.append({"role": role, "content": content})
    def to_messages(self) -> list[dict]: return self.messages[-self.window:]
    def compress(self, llm: LLM) -> str: return "sliding window: no compression needed"
    def reset(self): self.messages = []


class SummaryEngine(ContextEngine):
    """摘要策略：超阈值时用 LLM 摘要旧消息"""
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.messages: list[dict] = []
        self.summary: str = ""

    def add_message(self, role: str, content: str): self.messages.append({"role": role, "content": content})

    def to_messages(self) -> list[dict]:
        total = sum(len(str(m.get("content", ""))) for m in self.messages)
        if total > self.max_tokens and len(self.messages) > 4:
            # 需要压缩但由外部触发 compress（避免每次 to_messages 都调用 LLM）
            pass
        if self.summary:
            return [{"role": "user", "content": f"[摘要] {self.summary}"}] + self.messages[-10:]
        return self.messages[-40:]

    def compress(self, llm: LLM) -> str:
        if len(self.messages) < 4: return "太少无需压缩"
        self.summary = llm.chat([{"role": "user", "content": f"用中文简短总结（200字内）：\n{str(self.messages[:-4])}"}], temperature=0.0)
        self.messages = self.messages[-4:]
        return self.summary

    def reset(self): self.messages = []; self.summary = ""
