"""网页搜索工具 —— Bing（主） + DuckDuckGo（备）双引擎搜索"""

import os
import re
from urllib.request import urlopen, Request, quote, ProxyHandler, build_opener, install_opener
from html.parser import HTMLParser

from ddgs import DDGS  # DuckDuckGo 引擎

# 代理配置（从环境变量或 config.yaml 读取）
_proxy_url = os.getenv("HTTP_PROXY", os.getenv("http_proxy", ""))


def _get_proxy_handler() -> tuple:
    """获取 urllib 代理 handler，无代理时返回空 tuple"""
    try:
        import yaml
        cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml")))
        proxy = cfg.get("network", {}).get("proxy", "") if cfg else ""
        if proxy:
            return (ProxyHandler({"http": proxy, "https": proxy}),)
    except Exception:
        pass
    if _proxy_url:
        return (ProxyHandler({"http": _proxy_url, "https": _proxy_url}),)
    return ()


def _search_ddg(query: str, max_results: int) -> str | None:
    """DuckDuckGo 搜索，失败返回 None"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return "\n".join(
            f"{i}. {r.get('title', '无标题')}\n   链接: {r.get('href', '无链接')}\n   摘要: {r.get('body', '')[:150]}"
            for i, r in enumerate(results, 1)
        ) if results else None
    except Exception:
        return None


def _search_bing(query: str, max_results: int) -> str:
    """Bing 搜索（国内可用备用引擎）"""
    url = f"https://cn.bing.com/search?q={quote(query)}&count={max_results}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    # 带代理的 urlopen
    opener = build_opener(*_get_proxy_handler())
    html = opener.open(req, timeout=10).read().decode("utf-8", errors="ignore")
    # 正则提取搜索结果：标题 + 链接 + 摘要
    results = re.findall(
        r'<li class="b_algo".*?<h2.*?<a.*?href="(.*?)".*?>(.*?)</a>.*?<p[^>]*>(.*?)</p>',
        html, re.DOTALL
    )
    if not results:
        return f"未找到与 '{query}' 相关的结果"
    lines = []
    for i, (href, title, desc) in enumerate(results[:max_results], 1):
        title = re.sub(r"<[^>]+>", "", title).strip()  # 去除 HTML 标签
        desc = re.sub(r"<[^>]+>", "", desc).strip()[:150]
        lines.append(f"{i}. {title}\n   链接: {href}\n   摘要: {desc}")
    return "\n".join(lines)


def web_search(query: str, max_results: int = 5) -> str:
    """搜索网页：优先 Bing（国内快），失败时降级到 DuckDuckGo"""
    # 主引擎：Bing（国内可用）
    try:
        return _search_bing(query, max_results)
    except Exception:
        pass
    # 备用引擎：DuckDuckGo
    result = _search_ddg(query, max_results)
    if result:
        return result
    return f"搜索失败：Bing 和 DuckDuckGo 均不可用"


# 自注册
from src.tools.registry import register
from src.core.tool import Tool
register(Tool(
    name="web_search", description="搜索网页（DuckDuckGo+Bing）",
    parameters={"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}, "max_results": {"type": "integer", "description": "最多返回几条结果", "default": 5}}, "required": ["query"]},
    function=web_search,
))
