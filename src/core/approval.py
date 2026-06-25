"""审批系统 —— Hermes 对齐：危险操作需确认（ponytail: stdlib enum）"""

from enum import Enum


class ApprovalMode(str, Enum):
    ALWAYS = "always"  # 总是确认
    SMART = "smart"    # 仅危险命令确认（默认）
    YOLO = "yolo"      # 跳过所有确认

class ApprovalResult(str, Enum):
    ALLOW = "allow"    # 允许
    DENY = "deny"      # 拒绝


# 危险命令列表（子串匹配）
DANGEROUS_PATTERNS = [
    "rm -rf", "sudo ", "mkfs", "dd if=", "chmod 777", "reboot", "shutdown",
    "halt", "poweroff", ":(){", "> /dev/sda", "mkfs.", "fdisk", "mount /",
]


def check_dangerous(command: str) -> bool:
    """检查命令是否危险"""
    cmd_lower = command.strip().lower()
    return any(pattern in cmd_lower for pattern in DANGEROUS_PATTERNS)


# 全局审批模式
_approval_mode = ApprovalMode.SMART


def set_mode(mode: ApprovalMode):
    """设置审批模式"""
    global _approval_mode
    _approval_mode = mode


def get_mode() -> ApprovalMode:
    """获取当前审批模式"""
    return _approval_mode


def need_approval(command: str) -> bool:
    """判断是否需要审批"""
    if _approval_mode == ApprovalMode.YOLO:
        return False
    if _approval_mode == ApprovalMode.ALWAYS:
        return True
    return check_dangerous(command)  # SMART 模式
