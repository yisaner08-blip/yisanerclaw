"""协议定义 —— Hermes 对齐：结构化响应 + 流式事件 + JSON Schema（ponytail: stdlib dataclass）"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Callable, Any
import json


# === 停止原因 ===
class StopReason(str, Enum):
    COMPLETE = "complete"     # 正常完成
    MAX_STEPS = "max_steps"   # 超过最大步数
    DUPLICATE = "duplicate"   # 重复调用终止
    CANCELLED = "cancelled"   # 被用户取消
    ERROR = "error"           # 异常终止


# === Agent 响应结果（Hermes run_conversation 对齐） ===
@dataclass
class AgentResult:
    """Agent 执行结果，包含完整信息"""
    final_response: str        # 最终回复文本
    messages: list[dict]       # 完整消息历史（OpenAI 格式）
    stats: dict               # {tool_calls, steps, total_tokens}
    stop_reason: StopReason    # 停止原因

    def to_dict(self) -> dict:
        """转为 JSON 序列化字典"""
        return {
            "final_response": self.final_response,
            "messages": self.messages,
            "stats": self.stats,
            "stop_reason": self.stop_reason.value,
        }

    def to_json(self) -> str:
        """转为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# === 流式事件类型 ===
class StreamEvent(str, Enum):
    """流式输出中的事件类型"""
    STEP_START = "step_start"     # 开始一轮思考
    TOKEN = "token"               # 流式文本 token
    TOOL_CALL = "tool_call"       # 工具调用开始
    TOOL_RESULT = "tool_result"   # 工具调用结果
    STEP_END = "step_end"         # 一轮思考结束
    COMPLETE = "complete"         # 对话完成


@dataclass
class StreamChunk:
    """流式输出块"""
    event: StreamEvent  # 事件类型
    data: dict          # 事件数据 {step, token, tool_name, ...}

    def to_dict(self) -> dict:
        return {"event": self.event.value, "data": self.data}


# === 回调类型别名 ===
Callback = Callable[[str, dict], Any]  # (event_type, event_data)

# === 默认回调集 ===
DEFAULT_CALLBACKS: dict[str, Callback] = {
    "on_step": lambda data: None,          # 每轮思考：{step, thought}
    "on_tool_call": lambda data: None,      # 工具调用：{name, arguments}
    "on_tool_result": lambda data: None,    # 工具结果：{name, result}
    "on_token": lambda data: None,         # 流式 token：{token}
    "on_complete": lambda data: None,      # 完成：{result: AgentResult}
    "on_error": lambda data: None,         # 错误：{error}
}
