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
    for banned in BANNED_COMMANDS:
        if banned in cmd_lower:
            return f"错误：命令包含禁止的操作: {banned}"

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=None  # 继承当前工作目录
        )
        # 合并 stdout 和 stderr
        output = result.stdout + (f"\n[stderr]\n{result.stderr}" if result.stderr else "")
        output = output.strip() or "(命令执行成功，无输出)"
        return output[:2000] + "\n...(已截断)" if len(output) > 2000 else output
    except subprocess.TimeoutExpired:
        return f"错误：命令超时（>{timeout}秒）"
    except Exception as e:
        return f"错误：{e}"
