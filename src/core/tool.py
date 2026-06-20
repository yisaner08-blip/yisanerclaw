"""工具系统 —— 定义和注册工具，提供 OpenAI function calling 格式转换"""

import json
from pydantic import BaseModel, Field, PrivateAttr
from typing import Any, Callable


class Tool(BaseModel):
    name: str
    description: str
    parameters: dict
    function: Callable = Field(exclude=True)

    class Config:
        arbitrary_types_allowed = True


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_all(self) -> list[Tool]:
        return list(self._tools.values())

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"错误：工具 '{name}' 不存在"
        try:
            result = tool.function(**arguments)
            return str(result)
        except Exception as e:
            return f"错误：{e}"

    def to_openai_format(self) -> list[dict]:
        tools = []
        for tool in self._tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            })
        return tools
