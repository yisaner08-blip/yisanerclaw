"""计算器工具 —— 安全地计算数学表达式"""

import re
import math


def calculator(expression: str) -> str:
    """安全计算数学表达式，只允许数字、运算符和 math 函数

    Args:
        expression: 数学表达式，如 '2+3*4' 或 'math.sqrt(100)'
    Returns:
        计算结果或错误信息
    """
    # 安全沙箱：只允许有限的内置函数和 math 模块
    allowed_names = {"__builtins__": None}  # 禁用所有 builtin
    allowed_names.update({name: getattr(math, name) for name in dir(math) if not name.startswith("_")})

    try:
        # 先检查表达式是否只包含允许的字符
        if not re.match(r'^[\d\s\+\-\*\/\(\)\.\,\%\^A-Za-z_]+$', expression):
            return "错误：表达式包含不允许的字符"
        return str(eval(expression, allowed_names))  # 在受限命名空间执行
    except Exception as e:
        return f"错误：{e}"
