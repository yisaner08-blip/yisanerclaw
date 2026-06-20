"""网页搜索工具 —— 使用 DuckDuckGo 搜索网页"""

from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"未找到与 '{query}' 相关的结果"

        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")
            href = r.get("href", "无链接")
            body = r.get("body", "")[:150]
            lines.append(f"{i}. {title}")
            lines.append(f"   链接: {href}")
            lines.append(f"   摘要: {body}")
        return "\n".join(lines)
    except Exception as e:
        return f"搜索失败：{e}"
