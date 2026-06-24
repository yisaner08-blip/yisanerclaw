"""上下文构建器 —— 加载 SOUL.md、CONTEXT.md 并构建完整系统提示词（Hermes 风格）"""

import os


# 项目根目录（agent_project/）
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load_file(filename: str) -> str:
    """加载项目根目录下的 Markdown 文件"""
    path = os.path.join(_project_root, filename)
    return open(path, encoding="utf-8").read() if os.path.isfile(path) else ""


def build_system_prompt() -> str:
    """构建完整系统提示词：SOUL.md + CONTEXT.md + 行为规则"""
    soul = _load_file("SOUL.md")  # Agent 人格定义
    ctx = _load_file("CONTEXT.md")  # 项目上下文
    rules = (
        "<rules>\n"
        "- 已知道答案时直接回答，不要调用工具\n"
        "- 需要最新/外部信息时用 web_search 或 web_fetch\n"
        "- 需要文件操作时用 read_file/write_file/list_directory\n"
        "- 需要执行命令时用 run_shell\n"
        "- 数学计算用 calculator\n"
        "- 工具返回错误时，分析原因后修正参数重试（最多1次）\n"
        "- 回答简洁准确，优先用列表，避免冗长\n"
        "- 你的知识截止 2025年5月，之后的事件请用搜索工具\n"
        "</rules>"
    )
    return f"{soul}\n---\n{ctx}\n---\n{rules}".strip()
