"""Prompt 缓存 —— 系统提示词哈希检测，避免重复组装"""

import hashlib
import time


class PromptCache:
    """LRU 缓存系统提示词"""
    def __init__(self, max_entries: int = 10):
        self.cache: dict[str, tuple[str, float]] = {}  # hash → (content, timestamp)
        self.max_entries = max_entries

    def get(self, content: str) -> str | None:
        """检查缓存，命中返回原 content"""
        h = hashlib.md5(content.encode()).hexdigest()  # pocontail: stdlib hashlib
        if h in self.cache:
            self.cache[h] = (self.cache[h][0], time.time())  # 更新访问时间
            return content
        return None

    def set(self, content: str):
        """缓存系统提示词"""
        h = hashlib.md5(content.encode()).hexdigest()
        self.cache[h] = (content, time.time())
        if len(self.cache) > self.max_entries:
            oldest = min(self.cache, key=lambda k: self.cache[k][1])
            del self.cache[oldest]
