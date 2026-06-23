"""系统信息工具 —— 获取时间、环境等系统信息"""

import os
import sys
import platform
from datetime import datetime


def get_current_time() -> str:
    """获取当前日期时间（中文格式）"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")


def get_environment() -> str:
    """获取系统环境信息：Python 版本、OS、工作目录等"""
    return "\n".join([
        f"Python: {sys.version.split()[0]}",  # 仅取版本号
        f"OS: {platform.system()} {platform.release()}",
        f"主机名: {platform.node()}",
        f"工作目录: {os.getcwd()}",
        f"用户: {os.getenv('USER', os.getenv('USERNAME', 'unknown'))}",
    ])
