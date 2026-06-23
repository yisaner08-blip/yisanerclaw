"""Shell 执行工具 —— 安全地运行系统命令"""

import subprocess

BANNED_COMMANDS = ["sudo", "rm -rf /", "reboot", "shutdown", "halt", "poweroff",
                   "mkfs", "dd if=", ":(){ :|:& };:", "chmod 777 /"]


def run_shell(command: str, timeout: int = 30) -> str:
    # 安全检查：禁止危险命令
    cmd_lower = command.lower().strip()
    for banned in BANNED_COMMANDS:
        if banned in cmd_lower:
            return f"错误：命令包含禁止的操作: {banned}"

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=None  # 在用户当前工作目录执行
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        if not output.strip():
            output = "(命令执行成功，无输出)"
        return output[:2000] + "\n...(已截断)" if len(output) > 2000 else output
    except subprocess.TimeoutExpired:
        return f"错误：命令超时（>{timeout}秒）"
    except Exception as e:
        return f"错误：{e}"
