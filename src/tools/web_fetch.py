"""网页抓取工具 —— 获取网页内容并提取文本"""

from urllib.request import urlopen, Request
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            stripped = data.strip()
            if stripped:
                self.text.append(stripped)


def web_fetch(url: str, max_chars: int = 3000) -> str:
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Agent/1.0)"})
        with urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type.lower() and "text" not in content_type.lower():
                return f"错误：不支持的内容类型: {content_type}"
            html = resp.read().decode("utf-8", errors="ignore")

        parser = _TextExtractor()
        parser.feed(html)
        text = "\n".join(parser.text)
        if not text.strip():
            return "未能提取到页面文本内容"
        return text[:max_chars] if len(text) > max_chars else text
    except Exception as e:
        return f"抓取失败：{e}"
