"""系统信息工具 —— 获取时间、环境等系统信息"""

import os
import sys
import platform
from datetime import datetime


def get_current_time() -> str:
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S %A")


def get_environment() -> str:
    lines = [
        f"Python: {sys.version.split()[0]}",
        f"OS: {platform.system()} {platform.release()}",
        f"主机名: {platform.node()}",
        f"工作目录: {os.getcwd()}",
        f"用户: {os.getenv('USER', os.getenv('USERNAME', 'unknown'))}",
    ]
    return "\n".join(lines)
