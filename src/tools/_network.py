"""共享网络工具 —— 代理配置（ponytail: dup → extract shared）"""

import os
from urllib.request import ProxyHandler


def get_proxy_handler() -> tuple:
    """获取 urllib 代理 handler，从 config.yaml 或 HTTP_PROXY 环境变量读取"""
    proxy = os.getenv("HTTP_PROXY", os.getenv("http_proxy", ""))
    try:
        import yaml
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml")
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
        if cfg and (p := cfg.get("network", {}).get("proxy")):
            proxy = p
    except Exception:
        pass
    return (ProxyHandler({"http": proxy, "https": proxy}),) if proxy else ()
