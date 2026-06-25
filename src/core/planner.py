"""任务规划器 —— 将复杂任务分解为子任务"""

import re
from src.core.llm import LLM


class Planner:
    """用 LLM 将复杂任务分解为有序步骤"""

    def __init__(self, llm: LLM = None):
        self.llm = llm or LLM()  # LLM 客户端，用于生成分解方案

    def decompose(self, task: str) -> list[str]:
        """分解任务为步骤列表

        Args:
            task: 要分解的任务描述
        Returns:
            步骤字符串列表，空列表表示分解失败
        """
        prompt = (
            "把以下任务分解为子任务步骤。每步一行，按执行顺序排列。"
            "每行以数字开头（如 '1. '），只输出步骤本身，不要输出解释。\n\n"
            f"任务：{task}"
        )
        response = self.llm.chat([
            {"role": "system", "content": "你是任务规划专家，擅长将复杂任务分解为清晰的步骤。"},
            {"role": "user", "content": prompt},
        ])
        # 解析带编号的行，去掉前缀数字/符号
        steps = []
        for line in response.strip().split("\n"):
            s = line.strip()
            if s and (s[0].isdigit() or s.startswith("- ")):
                step = re.sub(r'^\d+[\.\)、\s\-]+', '', s)  # ponytail: stdlib — re.sub 替代 lstrip
                if step:
                    steps.append(step)
        return steps
