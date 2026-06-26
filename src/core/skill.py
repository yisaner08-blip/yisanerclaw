"""技能系统 —— Hermes 风格：标准化 SKILL.md 格式 + 自学习（ponytail: stdlib os/path）"""

import os
import json
import time

# 技能存储根目录
SKILL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "skills")


def _ensure_dir():
    os.makedirs(SKILL_DIR, exist_ok=True)


def save_skill(name: str, description: str, steps: list[str], tags: list[str] = None):
    """保存技能为标准化 SKILL.md 格式（Hermes 兼容）

    Args:
        name: 技能名称
        description: 简短描述
        steps: 步骤列表
        tags: 标签列表
    """
    _ensure_dir()
    skill_path = os.path.join(SKILL_DIR, name)
    os.makedirs(skill_path, exist_ok=True)

    content = f"---\nname: {name}\ndescription: {description}\nversion: 0.1.0\n"
    if tags:
        content += f"tags: [{', '.join(tags)}]\n"
    content += "---\n\n"
    content += f"# {name}\n\n"
    content += "## When to Use\n" + description + "\n\n"
    content += "## Procedure\n"
    for i, step in enumerate(steps, 1):
        content += f"{i}. {step}\n"
    content += "\n## Pitfalls\n- 注意：此技能由 Agent 自动生成，请验证后使用\n\n"
    content += "## Verification\n- 执行完成后检查预期结果\n"

    with open(os.path.join(skill_path, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(content)

    # 同时保存 JSON 格式用于快速列表
    json.dump({
        "name": name, "description": description, "steps": len(steps),
        "tags": tags or [], "created_at": time.time(),
    }, open(os.path.join(skill_path, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False)


def load_skill(name: str) -> dict | None:
    """加载技能的完整 SKILL.md 内容"""
    path = os.path.join(SKILL_DIR, name, "SKILL.md")
    return {"name": name, "content": open(path, encoding="utf-8").read()} if os.path.isfile(path) else None


def list_skills() -> list[dict]:
    """列出所有技能（快速索引）"""
    _ensure_dir()
    skills = []
    for name in sorted(os.listdir(SKILL_DIR)):
        meta_path = os.path.join(SKILL_DIR, name, "meta.json")
        if os.path.isfile(meta_path):
            s = json.load(open(meta_path, encoding="utf-8"))
            skills.append(s)
    return skills


def learn_skill(agent, task_description: str) -> str:
    """从对话中学习新技能（/learn 命令）

    Args:
        agent: 当前 Agent 实例
        task_description: 用户描述的任务/流程
    Returns:
        学习结果文本
    """
    steps_text = agent.compress_history()
    if "消息太少" in steps_text:
        return "当前对话内容太少，请在完成更多步骤后再学习"

    # 用 LLM 提取步骤
    prompt = f"请从以下对话摘要中提取关键步骤，每步一行，以数字开头：\n\n{steps_text}\n\n用户想学习的技能：{task_description}"
    steps_response = agent.llm.chat(
        [{"role": "user", "content": prompt}], temperature=0.0
    )

    # 提取编号行作为步骤
    steps = [
        s.lstrip("0123456789. -)）") for s in steps_response.strip().split("\n")
        if s.strip() and (s.strip()[0].isdigit() or s.strip().startswith("-"))
    ]

    if steps:
        save_skill(task_description, f"从对话学习：{task_description}", steps, ["learned"])
        return f"已学习技能：{task_description}（{len(steps)} 步）"
    return "未能提取有效步骤，请手动描述后再试"


def suggest_skill(agent) -> list[str] | None:
    """检测重复工具模式并建议技能

    Args:
        agent: 当前 Agent 实例
    Returns:
        建议的技能名称列表
    """
    from collections import Counter
    if len(agent._tool_seq) < 3:
        return None
    counts = Counter(agent._tool_seq[-10:])  # 最近 10 次调用
    return [n for n, c in counts.items() if c >= 2] if any(c >= 2 for c in counts.values()) else None
