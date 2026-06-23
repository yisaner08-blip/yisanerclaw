"""文件操作工具 —— 安全地读写文件和目录操作"""

import os

# workspace 目录：所有文件操作都限制在此目录内
WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _safe_path(filepath: str) -> str:
    """解析路径并确保在 workspace 内，防止路径穿越攻击"""
    full_path = os.path.abspath(os.path.join(WORKSPACE, filepath))
    if not full_path.startswith(WORKSPACE):
        raise PermissionError(f"不允许访问 workspace 外的路径: {filepath}")
    return full_path


def read_file(filepath: str) -> str:
    """读取文件内容，超出 2000 字符自动截断"""
    try:
        path = _safe_path(filepath)
        if not os.path.isfile(path):
            return f"错误：文件不存在: {filepath}"
        content = open(path, encoding="utf-8").read()
        return content[:2000] + "\n...(已截断)" if len(content) > 2000 else content
    except PermissionError as e:
        return f"错误：{e}"
    except Exception as e:
        return f"错误：{e}"


def write_file(filepath: str, content: str) -> str:
    """写入内容到文件，自动创建父目录"""
    try:
        path = _safe_path(filepath)
        os.makedirs(os.path.dirname(path), exist_ok=True)  # 确保父目录存在
        open(path, "w", encoding="utf-8").write(content)
        return f"成功：已写入 {filepath}"
    except PermissionError as e:
        return f"错误：{e}"
    except Exception as e:
        return f"错误：{e}"


def list_directory(dirpath: str = ".") -> str:
    """列出目录内容，标注文件和目录类型"""
    try:
        path = _safe_path(dirpath)
        if not os.path.isdir(path):
            return f"错误：目录不存在: {dirpath}"
        items = os.listdir(path)
        return "目录为空" if not items else "\n".join(
            f"{'[DIR] ' if os.path.isdir(os.path.join(path, i)) else '[FILE]'} {i}"
            for i in sorted(items)
        )
    except PermissionError as e:
        return f"错误：{e}"
    except Exception as e:
        return f"错误：{e}"
