"""LLM 调用封装 —— OpenAI-compatible API"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 加载 .env 中的 API Key 和配置


class LLM:
    """封装 OpenAI 兼容 API 的大模型客户端（Hermes fallback 对齐）"""

    def __init__(self, model=None, api_key=None, base_url=None, fallback_clients: list = None):
        self.model = model or os.getenv("MODEL_NAME", "deepseek-chat")
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
        )
        # Fallback 链：主客户端失败时依次尝试
        self._fallbacks = fallback_clients or []  # [(client, model_name), ...]

    def add_fallback(self, client, model_name: str):
        """添加降级客户端"""
        self._fallbacks.append((client, model_name))

    def _api_call(self, fn, *args, **kwargs) -> object:
        """执行 API 调用，失败时自动降级（Hermes fallback 对齐）"""
        errors = []
        # 1. 尝试主客户端
        try:
            return fn(self.client, self.model, *args, **kwargs)
        except Exception as e:
            errors.append(f"主: {e}")
        # 2. 依次尝试 fallback
        for client, model in self._fallbacks:
            try:
                return fn(client, model, *args, **kwargs)
            except Exception as e:
                errors.append(f"降级({model}): {e}")
        raise RuntimeError(f"所有 provider 均失败: {'; '.join(errors)}")

    def _raw_chat(self, client, model, messages, temperature):
        return client.chat.completions.create(model=model, messages=messages, temperature=temperature)

    def _raw_chat_with_tools(self, client, model, messages, tools, temperature):
        return client.chat.completions.create(model=model, messages=messages, tools=tools, temperature=temperature)

    def _raw_chat_stream(self, client, model, messages, tools, temperature):
        kwargs = {"model": model, "messages": messages, "temperature": temperature, "stream": True}
        if tools: kwargs["tools"] = tools
        return client.chat.completions.create(**kwargs)

    def chat(self, messages: list[dict], temperature=0.0) -> str:
        """发送消息给 LLM，返回纯文本回复"""
        resp = self._api_call(self._raw_chat, messages, temperature=temperature)
        return resp.choices[0].message.content

    def chat_with_tools(self, messages: list[dict], tools: list[dict], temperature=0.0):
        """调用 LLM，支持 tool calling，返回原始 message 对象"""
        resp = self._api_call(self._raw_chat_with_tools, messages, tools, temperature=temperature)
        return resp.choices[0].message

    def chat_stream(self, messages: list[dict], tools: list[dict] = None, temperature=0.0):
        """流式调用 LLM，逐 token yield（带 fallback）"""
        stream = self._api_call(self._raw_chat_stream, messages, tools, temperature=temperature)
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
