"""MCP 协议客户端 —— Hermes 对齐：stdio JSON-RPC 连接 MCP 服务器"""

import json
import subprocess
import uuid


class MCPClient:
    """MCP stdio 客户端：启动子进程并通信"""

    def __init__(self, name: str, command: str, args: list[str] = None):
        self.name = name  # 服务器名
        self.command = command  # 启动命令
        self.args = args or []
        self.process: subprocess.Popen | None = None
        self.server_info: dict = {}
        self.tools: list[dict] = []

    def connect(self) -> bool:
        """启动 MCP 服务器子进程并发送 initialize 请求"""
        try:
            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
            )
            # 发送 initialize 请求
            resp = self._request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "yisanerclaw", "version": "0.1.0"}
            })
            self.server_info = resp.get("result", {}).get("serverInfo", {}) if resp else {}
            # 发现工具
            tools_resp = self._request("tools/list", {})
            self.tools = tools_resp.get("result", {}).get("tools", []) if tools_resp else []
            return bool(self.tools)
        except Exception:
            return False

    def _request(self, method: str, params: dict) -> dict | None:
        """发送 JSON-RPC 请求"""
        if not self.process or self.process.poll() is not None:
            return None
        msg = {
            "jsonrpc": "2.0", "id": uuid.uuid4().hex[:8],
            "method": method, "params": params,
        }
        try:
            self.process.stdin.write(json.dumps(msg) + "\n")
            self.process.stdin.flush()
            response = self.process.stdout.readline()
            return json.loads(response) if response else None
        except Exception:
            return None

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """调用 MCP 工具并返回结果"""
        resp = self._request("tools/call", {"name": tool_name, "arguments": arguments})
        if resp and "result" in resp:
            content = resp["result"].get("content", [])
            return "\n".join(c.get("text", str(c)) for c in content)
        return f"MCP 调用失败: {resp.get('error', 'unknown')}" if resp else "MCP 连接断开"

    def disconnect(self):
        if self.process:
            self.process.terminate()
            self.process = None


# 全局已连接 MCP 服务器
_clients: dict[str, MCPClient] = {}


def connect_mcp(name: str, command: str, args: list[str] = None) -> bool:
    """连接 MCP 服务器"""
    client = MCPClient(name, command, args)
    if client.connect():
        _clients[name] = client
        return True
    return False


def list_mcp() -> list[dict]:
    """列出已连接服务器"""
    return [{"name": k, "tools": len(c.tools)} for k, c in _clients.items()]
