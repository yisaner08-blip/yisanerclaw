"""简单技能系统 —— 保存/加载/执行复用步骤流程（Hermes 风格简化版）"""

import os
import json
import time

# 技能存储目录
_skill_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "skills")
os.makedirs(_skill_dir, exist_ok=True)


def save_skill(name: str, description: str, steps: list[str]):
    """保存技能到 JSON 文件

    Args:
        name: 技能名称（用作文件名）
        description: 技能描述
        steps: 步骤列表
    """
    path = os.path.join(_skill_dir, f"{name}.json")
    data = {
        "name": name, "description": description, "steps": steps,
        "created_at": time.time(),
    }
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def load_skill(name: str) -> dict | None:
    """加载指定技能"""
    path = os.path.join(_skill_dir, f"{name}.json")
    return json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else None


def list_skills() -> list[dict]:
    """列出所有已保存技能"""
    skills = []
    for f in sorted(os.listdir(_skill_dir)):
        if f.endswith(".json"):
            s = json.load(open(os.path.join(_skill_dir, f), encoding="utf-8"))
            skills.append({"name": s["name"], "description": s["description"], "steps": len(s["steps"])})
    return skills
