"""文本浏览器 —— 增强 web_fetch：表单提交 + 链接跟踪"""

import re
from urllib.request import urlopen, Request, build_opener, quote
from urllib.parse import urljoin
from src.tools._network import get_proxy_handler


def browse_fetch(url: str) -> str:
    """抓取网页内容并返回文本"""
    opener = build_opener(*get_proxy_handler())
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Agent/1.0)"})
    with opener.open(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def browse_links(url: str, max_links: int = 20) -> str:
    """列出网页中的所有链接"""
    html = browse_fetch(url)
    links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>', html, re.IGNORECASE)
    lines = []
    for href, text in links[:max_links]:
        text = re.sub(r'<[^>]+>', '', text).strip()[:60] or "(无文本)"
        full_url = urljoin(url, href)
        lines.append(f"  [{text}]({full_url})")
    return f"页面链接 ({len(links)} 个):\n" + "\n".join(lines) if lines else "未找到链接"


def browse_submit(url: str, form_data: str) -> str:
    """提交表单（POST 请求）"""
    opener = build_opener(*get_proxy_handler())
    data = form_data.encode("utf-8") if isinstance(form_data, str) else form_data
    req = Request(url, data=data, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"})
    with opener.open(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore")


# 自注册
from src.tools.registry import register
from src.core.tool import Tool
register(Tool(name="browse_links", description="列出网页中的所有链接", parameters={"type": "object", "properties": {"url": {"type": "string", "description": "网页 URL"}, "max_links": {"type": "integer", "default": 20}}, "required": ["url"]}, function=browse_links))
