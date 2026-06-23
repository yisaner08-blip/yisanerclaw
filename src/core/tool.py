"""工具系统 —— 定义和注册工具，提供 OpenAI function calling 格式转换"""

from pydantic import BaseModel, Field
from typing import Any, Callable


class Tool(BaseModel):
    """单个工具定义：名称、描述、参数 Schema、执行函数"""
    name: str                    # 工具唯一名称，LLM 用于识别
    description: str             # 工具描述，LLM 据此决定是否调用
    parameters: dict             # JSON Schema 参数定义
    function: Callable = Field(exclude=True)  # 实际执行的 Python 函数（不序列化）

    class Config:
        arbitrary_types_allowed = True  # 允许 Callable 类型字段


class ToolRegistry:
    """工具注册表 —— 管理所有可用工具，提供注册/执行/格式转换"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}  # name → Tool 映射

    def register(self, tool: Tool) -> None:
        """注册工具，按 name 索引"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """根据名称获取工具，不存在返回 None"""
        return self._tools.get(name)

    def list_all(self) -> list[Tool]:
        """返回所有已注册工具"""
        return list(self._tools.values())

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """执行工具并返回结果字符串（含错误信息）

        Args:
            name: 工具名称
            arguments: 参数字典
        Returns:
            执行结果（成功或错误信息）
        """
        tool = self._tools.get(name)
        return f"错误：工具 '{name}' 不存在" if not tool else _call_tool(tool, arguments)

    def to_openai_format(self) -> list[dict]:
        """将所有工具转为 OpenAI function calling 格式"""
        return [
            {"type": "function", "function": {
                "name": t.name, "description": t.description, "parameters": t.parameters,
            }}
            for t in self._tools.values()
        ]


def _call_tool(tool: Tool, arguments: dict[str, Any]) -> str:
    """调用工具函数并转为字符串，捕获异常"""
    try:
        return str(tool.function(**arguments))
    except Exception as e:
        return f"错误：{e}"
