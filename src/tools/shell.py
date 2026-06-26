"""Shell 执行工具 —— 安全地运行系统命令"""

import subprocess

# 禁止的危险命令列表（子串匹配检查）
BANNED_COMMANDS = [
    "sudo", "rm -rf /", "reboot", "shutdown", "halt", "poweroff",
    "mkfs", "dd if=", ":(){ :|:& };:", "chmod 777 /",
]


def run_shell(command: str, timeout: int = 30) -> str:
    """安全执行 shell 命令并返回输出

    Args:
        command: 要执行的命令字符串
        timeout: 超时秒数，默认 30
    Returns:
        命令的输出（stdout+stderr），或错误信息
    """
    # 次责除 b 匹配禁止命令（不区分大小写）
    cmd_lower = command.lower().strip()
    # Hermes 对齐：审批检查（先检查新的审批系统）
    from src.core.approval import need_approval as _need_approval, check_dangerous
    if check_dangerous(cmd_lower):
        return f"错误：危险命令被拦截: {command}"
    for banned in BANNED_COMMANDS:
        if banned in cmd_lower:
            return f"错误：命令包含禁止的操作: {banned}"

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=None  # 继承当前工作目录
        )
        output = (result.stdout + (f"\n[stderr]\n{result.stderr}" if result.stderr else "")).strip() or "(命令执行成功，无输出)"
        return output[:2000] + "\n...(已截断)" if len(output) > 2000 else output
    except subprocess.TimeoutExpired:
        return f"错误：命令超时（>{timeout}秒）"
    except Exception as e:
        return f"错误：{e}"


def run_ssh(host: str, command: str, timeout: int = 30) -> str:
    """SSH 远程执行命令（Phase 7：Hermes 多终端对齐）

    Args:
        host: SSH 主机地址（user@host:port）
        command: 要执行的命令
        timeout: 超时秒数
    Returns:
        命令输出或错误信息
    """
    import subprocess
    host_part = host.split(":")[0] if ":" in host else host
    port = host.split(":")[1] if ":" in host else "22"
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-p", port, host_part, command],
            capture_output=True, text=True, timeout=timeout,
        )
        output = (result.stdout + (f"\n[stderr]\n{result.stderr}" if result.stderr else "")).strip() or "(命令执行成功，无输出)"
        return output[:2000] + "\n...(已截断)" if len(output) > 2000 else output
    except subprocess.TimeoutExpired:
        return f"错误：SSH 命令超时（>{timeout}秒）"
    except FileNotFoundError:
        return "错误：未找到 ssh 客户端，请安装 openssh-client"
    except Exception as e:
        return f"SSH 错误：{e}"

# 自注册
from src.tools.registry import register
from src.core.tool import Tool
register(Tool(
    name="run_shell", description="执行安全的 shell 命令并返回输出",
    parameters={"type": "object", "properties": {"command": {"type": "string", "description": "要执行的命令"}}, "required": ["command"]},
    function=run_shell,
))
register(Tool(
    name="run_ssh", description="SSH 远程执行命令",
    parameters={"type": "object", "properties": {"host": {"type": "string", "description": "SSH 主机 user@host:port"}, "command": {"type": "string", "description": "要执行的命令"}}, "required": ["host", "command"]},
    function=run_ssh,
))
