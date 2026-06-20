"""文件操作工具 —— 安全地读写文件和目录操作"""

import os


WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _safe_path(filepath: str) -> str:
    """确保路径在 workspace 内，防止路径穿越攻击"""
    full_path = os.path.abspath(os.path.join(WORKSPACE, filepath))
    if not full_path.startswith(WORKSPACE):
        raise PermissionError(f"不允许访问 workspace 外的路径: {filepath}")
    return full_path


def read_file(filepath: str) -> str:
    try:
        path = _safe_path(filepath)
        if not os.path.isfile(path):
            return f"错误：文件不存在: {filepath}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return content[:5000] if len(content) > 5000 else content
    except PermissionError as e:
        return f"错误：{e}"
    except Exception as e:
        return f"错误：{e}"


def write_file(filepath: str, content: str) -> str:
    try:
        path = _safe_path(filepath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"成功：已写入 {filepath}"
    except PermissionError as e:
        return f"错误：{e}"
    except Exception as e:
        return f"错误：{e}"


def list_directory(dirpath: str = ".") -> str:
    try:
        path = _safe_path(dirpath)
        if not os.path.isdir(path):
            return f"错误：目录不存在: {dirpath}"
        items = os.listdir(path)
        if not items:
            return f"目录 {dirpath} 为空"
        lines = []
        for item in sorted(items):
            full = os.path.join(path, item)
            prefix = "[DIR] " if os.path.isdir(full) else "[FILE]"
            lines.append(f"{prefix} {item}")
        return "\n".join(lines)
    except PermissionError as e:
        return f"错误：{e}"
    except Exception as e:
        return f"错误：{e}"
