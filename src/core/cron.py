"""Cron 定时任务系统 —— Hermes 风格：4 种调度格式 + JSON 持久化（ponytail: stdlib json/os/time）"""

import os
import json
import time
import re
import uuid
from datetime import datetime, timedelta

# 任务存储路径
CRON_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cron")
JOBS_FILE = os.path.join(CRON_DIR, "jobs.json")


def _ensure_dir():
    os.makedirs(CRON_DIR, exist_ok=True)


def _load_jobs() -> list[dict]:
    """加载所有定时任务"""
    _ensure_dir()
    return json.load(open(JOBS_FILE, encoding="utf-8")) if os.path.isfile(JOBS_FILE) else []


def _save_jobs(jobs: list[dict]):
    """原子写入任务列表"""
    _ensure_dir()
    tmp = JOBS_FILE + ".tmp"
    json.dump(jobs, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.replace(tmp, JOBS_FILE)


def _parse_schedule(schedule: str) -> tuple[str, float | None]:
    """解析调度表达式，返回 (类型, 下次运行相对秒数)

    支持格式：
    - 30m / 2h / 1d → 相对延迟
    - every 30m / every 2h → 间隔
    - 0 9 * * * → Cron（简化：仅支持 5 字段）
    - 2026-03-15T09:00:00 → ISO 时间戳
    """
    s = schedule.strip()
    # ISO 时间戳
    if "T" in s:
        try:
            target = datetime.fromisoformat(s)
            return ("iso", (target - datetime.now()).total_seconds())
        except ValueError:
            raise ValueError(f"无效的 ISO 时间戳: {s}")

    # every N 格式
    m = re.match(r"every\s+(\d+)(m|h|d)", s)
    if m:
        value, unit = int(m.group(1)), m.group(2)
        return ("interval", {"m": 60, "h": 3600, "d": 86400}[unit] * value)

    # Nm/Nh/Nd 格式
    m = re.match(r"^(\d+)(m|h|d)$", s)
    if m:
        value, unit = int(m.group(1)), m.group(2)
        return ("relative", {"m": 60, "h": 3600, "d": 86400}[unit] * value)

    # Cron 表达式
    if len(s.split()) == 5:
        return ("cron", _cron_next_seconds(s))

    raise ValueError(f"不支持的调度格式: {s}")


def _cron_next_seconds(expr: str) -> float:
    """简化 Cron 解析：仅支持固定时间和 */N 格式"""
    parts = expr.split()
    now = datetime.now()
    hour = int(parts[1]) if parts[1] != "*" else now.hour
    minute = int(parts[0]) if parts[0] != "*" else now.minute
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def add_job(schedule: str, task: str) -> str:
    """创建定时任务，返回 job_id"""
    sched_type, seconds = _parse_schedule(schedule)
    job_id = uuid.uuid4().hex[:8]
    job = {
        "id": job_id, "task": task, "schedule": schedule,
        "type": sched_type, "interval": seconds,
        "next_run": (datetime.now() + timedelta(seconds=seconds)).isoformat(),
        "paused": False, "created_at": datetime.now().isoformat(),
    }
    jobs = _load_jobs()
    jobs.append(job)
    _save_jobs(jobs)
    return job_id


def list_jobs() -> list[dict]:
    """列出所有任务"""
    return _load_jobs()


def remove_job(job_id: str) -> bool:
    """删除任务"""
    jobs = _load_jobs()
    filtered = [j for j in jobs if j["id"] != job_id]
    if len(filtered) == len(jobs):
        return False
    _save_jobs(filtered)
    return True


def pause_job(job_id: str) -> bool:
    """暂停任务"""
    return _toggle_job(job_id, True)


def resume_job(job_id: str) -> bool:
    """恢复任务"""
    return _toggle_job(job_id, False)


def _toggle_job(job_id: str, paused: bool) -> bool:
    jobs = _load_jobs()
    for j in jobs:
        if j["id"] == job_id:
            j["paused"] = paused
            _save_jobs(jobs)
            return True
    return False


def tick():
    """执行到期的定时任务（运行 callback），每个到期任务最多一条"""
    jobs = _load_jobs()
    now = datetime.now()
    updated = False
    results = []
    for j in jobs:
        if j["paused"]:
            continue
        next_run = datetime.fromisoformat(j["next_run"])
        if next_run > now:
            continue
        results.append(j["task"])  # 返回到期任务文本
        if j["type"] in ("interval", "relative", "cron"):
            # 重新计算下次运行
            _, seconds = _parse_schedule(j["schedule"])
            j["next_run"] = (now + timedelta(seconds=seconds)).isoformat()
            updated = True
        else:
            # ISO 时间戳一次性任务 → 标记暂停
            j["paused"] = True
            updated = True
    if updated:
        _save_jobs(jobs)
    return results
