"""工具注册表 —— 全局单例，工具文件导入时自注册"""

from src.core.tool import Tool, ToolRegistry

# 全局单例（Hermes 风格：导入时自动发现工具）
_registry = ToolRegistry()


def register(tool: Tool):
    """工具自注册入口，所有 src/tools/*.py 在文件底部调用"""
    _registry.register(tool)


def get_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    return _registry
