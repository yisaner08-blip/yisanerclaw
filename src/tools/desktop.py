"""桌面控制工具 —— xdotool 截图和模拟输入（Linux 环境）"""

import subprocess
import os
import tempfile


def screenshot() -> str:
    """截图并返回文件路径"""
    path = os.path.join(tempfile.gettempdir(), f"screenshot_{int(__import__('time').time())}.png")
    try:
        subprocess.run(["gnome-screenshot", "-f", path], capture_output=True, timeout=10)
    except Exception:
        try:
            subprocess.run(["scrot", path], capture_output=True, timeout=10)
        except Exception:
            return "错误：未找到截图工具（gnome-screenshot 或 scrot）"
    return f"截图已保存: {path}"


def type_text(text: str) -> str:
    """模拟键盘输入文本"""
    try:
        subprocess.run(["xdotool", "type", text], capture_output=True, timeout=5)
        return f"已输入: {text}"
    except FileNotFoundError:
        return "错误：未安装 xdotool"
    except Exception as e:
        return f"输入失败: {e}"


def click(x: int, y: int) -> str:
    """鼠标点击指定坐标"""
    try:
        subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "1"], capture_output=True, timeout=5)
        return f"已点击 ({x}, {y})"
    except FileNotFoundError:
        return "错误：未安装 xdotool"
    except Exception as e:
        return f"点击失败: {e}"


# 自注册
from src.tools.registry import register
from src.core.tool import Tool
register(Tool(name="screenshot", description="截取桌面屏幕", parameters={"type": "object", "properties": {}}, function=screenshot))
register(Tool(name="type_text", description="模拟键盘输入文本", parameters={"type": "object", "properties": {"text": {"type": "string", "description": "要输入的文本"}}, "required": ["text"]}, function=type_text))
register(Tool(name="click", description="鼠标点击指定坐标", parameters={"type": "object", "properties": {"x": {"type": "integer", "description": "X坐标"}, "y": {"type": "integer", "description": "Y坐标"}}, "required": ["x", "y"]}, function=click))
