"""迭代预算 —— Hermes 对齐：控制 Agent 循环次数（ponytail: stdlib dataclass）"""

from dataclasses import dataclass


@dataclass
class IterationBudget:
    """Agent 迭代预算：防止无限循环"""
    max_iterations: int = 90      # 最大迭代次数（父代理）
    subagent_cap: int = 50        # 子代理上限

    def __post_init__(self):
        self.remaining = self.max_iterations
        self.sub_remaining = self.subagent_cap

    def consume(self) -> bool:
        """消耗一次迭代，返回是否还有余额"""
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        return True

    def sub_consume(self) -> bool:
        """消耗子代理迭代"""
        if self.sub_remaining <= 0:
            return False
        self.sub_remaining -= 1
        return True

    def reset(self):
        """重置预算"""
        self.remaining = self.max_iterations
        self.sub_remaining = self.subagent_cap

    @property
    def exhausted(self) -> bool:
        return self.remaining <= 0

    @property
    def sub_exhausted(self) -> bool:
        return self.sub_remaining <= 0

    @property
    def usage_pct(self) -> float:
        return (self.max_iterations - self.remaining) / self.max_iterations * 100
