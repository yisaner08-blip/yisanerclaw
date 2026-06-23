"""LLM 调用封装 —— OpenAI-compatible API"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 加载 .env 中的 API Key 和配置


class LLM:
    """封装 OpenAI 兼容 API 的大模型客户端"""

    def __init__(self, model=None, api_key=None, base_url=None):
        """初始化 LLM 客户端，优先用传入参数，其次从环境变量读取

        Args:
            model: 模型名，默认读取 MODEL_NAME 环境变量
            api_key: API 密钥，默认读取 OPENAI_API_KEY
            base_url: API 地址，默认读取 OPENAI_BASE_URL
        """
        self.model = model or os.getenv("MODEL_NAME", "deepseek-chat")  # 模型标识
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),  # API 密钥
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),  # API 基础地址
        )

    def chat(self, messages: list[dict], temperature=0.0) -> str:
        """发送消息给 LLM，返回纯文本回复（不含工具调用）

        Args:
            messages: 对话历史列表 [{"role": "user", "content": "..."}]
            temperature: 随机性参数，0 表示确定性输出
        Returns:
            LLM 的文本回复
        """
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature,
        )
        return response.choices[0].message.content  # 提取回复文本

    def chat_with_tools(self, messages: list[dict], tools: list[dict], temperature=0.0):
        """调用 LLM，支持 tool calling。返回原始 message 对象

        Args:
            messages: 对话历史
            tools: OpenAI function calling 格式的工具定义
            temperature: 随机性
        Returns:
            message 对象，可通过 .content 和 .tool_calls 分别获取文本和工具调用
        """
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, tools=tools, temperature=temperature,
        )
        return response.choices[0].message  # 返回完整消息对象
