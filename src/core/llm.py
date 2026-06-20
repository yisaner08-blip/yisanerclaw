"""LLM 调用封装 —— OpenAI-compatible API"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLM:
    def __init__(self, model=None, api_key=None, base_url=None):
        self.model = model or os.getenv("MODEL_NAME", "deepseek-chat")
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
        )

    def chat(self, messages: list[dict], temperature=0.0) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content

    def chat_with_tools(self, messages: list[dict], tools: list[dict], temperature=0.0):
        """调用 LLM，支持 tool calling。返回原始 message 对象，可访问 .content 和 .tool_calls"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            temperature=temperature,
        )
        return response.choices[0].message
