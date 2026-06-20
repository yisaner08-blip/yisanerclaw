"""任务规划器 —— 将复杂任务分解为子任务"""

from src.core.llm import LLM


class Planner:
    def __init__(self, llm: LLM = None):
        self.llm = llm or LLM()

    def decompose(self, task: str) -> list[str]:
        prompt = (
            "把以下任务分解为子任务步骤。每步一行，按执行顺序排列。"
            "每行以数字开头（如 '1. '），只输出步骤本身，不要输出解释。\n\n"
            f"任务：{task}"
        )
        response = self.llm.chat([
            {"role": "system", "content": "你是一个任务规划专家，擅长将复杂任务分解为清晰的步骤。"},
            {"role": "user", "content": prompt},
        ])
        steps = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("- ")):
                # 去掉数字前缀或 dash
                step = line.lstrip("0123456789. -)）")
                if step:
                    steps.append(step)
        return steps
