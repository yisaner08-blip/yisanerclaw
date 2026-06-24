"""网页搜索工具 —— 使用 DuckDuckGo 搜索网页"""

from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> str:
    """搜索网页并返回格式化的结果（标题+链接+摘要）

    Args:
        query: 搜索关键词
        max_results: 最多返回结果数，默认 5
    Returns:
        格式化的搜索结果或错误信息
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return "未找到相关结果" if not results else "\n".join(
            f"{i}. {r.get('title', '无标题')}\n"
            f"   链接: {r.get('href', '无链接')}\n"
            f"   摘要: {r.get('body', '')[:150]}"
            for i, r in enumerate(results, 1)
        )
    except Exception as e:
        return f"搜索失败：{e}"

# 自注册
from src.tools.registry import register
from src.core.tool import Tool
register(Tool(
    name="web_search", description="搜索网页，返回标题、链接和摘要",
    parameters={"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}, "max_results": {"type": "integer", "description": "最多返回几条结果", "default": 5}}, "required": ["query"]},
    function=web_search,
))
