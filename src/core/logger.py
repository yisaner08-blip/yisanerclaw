"""日志系统 —— 文件 + 终端双输出（Python logging 标准模块）"""

import os
import logging

_log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "logs")
os.makedirs(_log_dir, exist_ok=True)

# 根 logger
_logger = logging.getLogger("yisanerclaw")
_logger.setLevel(logging.DEBUG)

# 文件 handler
_fh = logging.FileHandler(os.path.join(_log_dir, "agent.log"), encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
_logger.addHandler(_fh)

# 终端 handler（INFO 以上）
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
_logger.addHandler(_ch)

LOGGER = _logger  # ponytail: stdlib — 直接 logging.getLogger，无需包装函数


