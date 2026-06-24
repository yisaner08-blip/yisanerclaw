"""LLM Provider 注册表 —— 支持多模型切换（DeepSeek / OpenAI / 自定义）"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# Provider 配置注册表
PROVIDERS = {
    "deepseek": {
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    },
    "openai": {
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
    },
}


def create_client(provider: str = None) -> OpenAI:
    """根据 provider 名创建 OpenAI 兼容客户端

    Args:
        provider: provider 名称（deepseek/openai），默认用 OPENAI_API_KEY 兼容
    Returns:
        配置好的 OpenAI 客户端
    """
    # 默认：兼容 OPENAI_API_KEY + OPENAI_BASE_URL 环境变量
    if provider is None or provider not in PROVIDERS:
        return OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
        )
    cfg = PROVIDERS[provider]
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def get_model_name(provider: str = None) -> str:
    """获取当前 provider 的模型名"""
    if provider and provider in PROVIDERS:
        return PROVIDERS[provider]["model"]
    return os.getenv("MODEL_NAME", "deepseek-v4-flash")
