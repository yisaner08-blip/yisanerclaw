"""网页抓取工具 —— 获取网页内容并提取文本"""

from urllib.request import urlopen, Request
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    """HTML 文本提取器：过滤 script/style 标签，收集可见文本"""

    def __init__(self):
        super().__init__()
        self.text = []   # 收集的文本片段
        self.skip = False  # 是否跳过当前标签内容（script/style 内）

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip = True  # 进入跳过模式

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = False  # 退出跳过模式

    def handle_data(self, data):
        if not self.skip and (stripped := data.strip()):
            self.text.append(stripped)


def web_fetch(url: str, max_chars: int = 2000) -> str:
    """抓取网页内容并提取纯文本

    Args:
        url: 网页 URL
        max_chars: 最大返回字符数，默认 2000
    Returns:
        提取的文本内容或错误信息
    """
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Agent/1.0)"})
        with urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type.lower() and "text" not in content_type.lower():
                return f"错误：不支持的内容类型: {content_type}"
            html = resp.read().decode("utf-8", errors="ignore")

        parser = _TextExtractor()
        parser.feed(html)
        text = "\n".join(parser.text).strip() or "未能提取到页面文本内容"
        return text[:max_chars] + "\n...(已截断)" if len(text) > max_chars else text
    except Exception as e:
        return f"抓取失败：{e}"

# 自注册
from src.tools.registry import register
from src.core.tool import Tool
register(Tool(
    name="web_fetch", description="抓取网页内容，提取正文文本",
    parameters={"type": "object", "properties": {"url": {"type": "string", "description": "要抓取的网页 URL"}}, "required": ["url"]},
    function=web_fetch,
))
