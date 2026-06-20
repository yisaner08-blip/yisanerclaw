"""计算器工具 —— 安全地计算数学表达式"""

import re
import math


def calculator(expression: str) -> str:
    allowed_names = {"__builtins__": None}
    allowed_names.update({
        "abs": abs, "round": round, "min": min, "max": max,
        "pow": pow, "math": math,
    })

    try:
        if not re.match(r'^[\d\s\+\-\*\/\(\)\.\,\%\^A-Za-z_]+$', expression):
            return f"错误：表达式包含不允许的字符"
        result = eval(expression, allowed_names)
        return str(result)
    except Exception as e:
        return f"错误：{e}"
