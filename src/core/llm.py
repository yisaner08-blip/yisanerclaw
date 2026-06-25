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
        """发送消息给 LLM，返回纯文本回复"""
        return self.client.chat.completions.create(model=self.model, messages=messages, temperature=temperature).choices[0].message.content

    def chat_with_tools(self, messages: list[dict], tools: list[dict], temperature=0.0):
        """调用 LLM，支持 tool calling，返回原始 message 对象"""
        return self.client.chat.completions.create(model=self.model, messages=messages, tools=tools, temperature=temperature).choices[0].message

    def chat_stream(self, messages: list[dict], tools: list[dict] = None, temperature=0.0):
        """流式调用 LLM，逐 token yield（Hermes stream_delta_callback 对齐）

        Yields:
            dict: {"type": "token", "content": "..."}  — 文本 token
            dict: {"type": "tool_call", "name": "...", "arguments": "..."}  — 完成的工具调用
            dict: {"type": "done", "message": message}  — 流结束，携带完整 message
        """
        kwargs = {"model": self.model, "messages": messages, "temperature": temperature, "stream": True}
        if tools:
            kwargs["tools"] = tools
        stream = self.client.chat.completions.create(**kwargs)

        content_buf = ""
        tool_calls_buf: dict[int, dict] = {}  # index → {name, arguments}
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue
            # 文本 token
            if delta.content:
                content_buf += delta.content
                yield {"type": "token", "content": delta.content}
            # 工具调用（分块到达）
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_buf:
                        tool_calls_buf[idx] = {"id": tc.id or "", "name": tc.function.name or "", "arguments": ""}
                    if tc.function.name:
                        tool_calls_buf[idx]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls_buf[idx]["arguments"] += tc.function.arguments
        # 构建完整 message 对象
        from types import SimpleNamespace
        msg = SimpleNamespace()
        msg.content = content_buf.strip() or None
        msg.tool_calls = None
        if tool_calls_buf:
            tcs = []
            for _, tc in sorted(tool_calls_buf.items()):
                tc_obj = SimpleNamespace()
                tc_obj.id = tc["id"]
                tc_obj.function = SimpleNamespace()
                tc_obj.function.name = tc["name"]
                tc_obj.function.arguments = tc["arguments"]
                tc_obj.type = "function"
                tcs.append(tc_obj)
            msg.tool_calls = tcs
        yield {"type": "done", "message": msg}
