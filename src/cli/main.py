"""CLI 交互界面 —— 在终端里和 Agent 对话"""

import time
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from src.core.llm import LLM
from src.core.agent import Agent
from src.core.planner import Planner
from src.core.vector_memory import VectorMemory
from src.core.session import save_session, list_sessions  # 持久化会话
from src.core.session import search_sessions  # FTS5 全文搜索
from src.core.skill import list_skills, save_skill, load_skill  # 技能系统
from src.core.skill import learn_skill  # /learn 命令
from src.core import cron  # Cron 定时任务
from src.core.mcp_client import connect_mcp, list_mcp  # MCP
import src.tools.browse  # noqa: F401  Phase 4: 文本浏览器
import src.tools.tts     # noqa: F401  Phase 5: TTS
import src.tools.desktop # noqa: F401  Phase 6: 桌面控制

# Phase 3: Hook 系统
_hooks: dict[str, list[str]] = {"pre_tool": [], "post_tool": [], "on_start": [], "on_complete": []}

# 导入工具模块触发自注册（Hermes 风格：不直接使用，仅触发 registry.register）
import src.tools.calculator  # noqa: F401
import src.tools.file_ops    # noqa: F401
import src.tools.web_search  # noqa: F401
import src.tools.web_fetch   # noqa: F401
import src.tools.shell       # noqa: F401
import src.tools.system_info # noqa: F401
from src.tools.registry import get_registry


def create_agent(vm=None) -> Agent:
    """创建 Agent，使用工具模块自注册的全局注册表"""
    return Agent(llm=LLM(), tool_registry=get_registry(), vector_memory=vm)


def main():
    console = Console()
    console.print(Panel.fit(
        "[bold cyan]yisanerclaw[/bold cyan] — ReAct Agent (9 工具)\n"
        "[bold blue]/plan[/bold blue] 分解  [bold blue]/run[/bold blue] 执行  [bold blue]/remember[/bold blue] 记忆\n"
        "[bold blue]/recall[/bold blue] 检索  [bold blue]/compress[/bold blue] 压缩  [bold blue]/usage[/bold blue] 统计\n"
        "[bold blue]/sessions[/bold blue] 历史  [bold red]退出/exit/q[/bold red]  [bold yellow]reset[/bold yellow] 清除",
        title="欢迎"
    ))

    vm = VectorMemory()
    agent = create_agent(vm=vm)
    planner = Planner(llm=agent.llm)

    while True:
        try:
            user_input = console.input("\n[bold green]你:[/bold green] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]再见！[/yellow]")
            break

        cmd = user_input.strip()
        if cmd.lower() in ("退出", "exit", "quit", "q"):
            console.print("[yellow]再见！[/yellow]")
            break
        if cmd.lower() == "reset":
            agent.reset_memory()
            console.print("[yellow]记忆已清除[/yellow]")
            continue
        if not cmd:
            continue

        # /plan 命令：仅分解不执行
        if cmd.startswith("/plan "):
            task = cmd[len("/plan "):].strip()
            with console.status("[cyan]规划中...[/cyan]"):
                steps = planner.decompose(task)
            if steps:
                table = Table(title=f"任务分解: {task}", border_style="cyan")
                table.add_column("#", style="dim")
                table.add_column("步骤")
                for i, step in enumerate(steps, 1):
                    table.add_row(str(i), step)
                console.print(table)
            else:
                console.print("[yellow]未能分解任务[/yellow]")
            continue

        # /run 命令：分解并逐步执行
        if cmd.startswith("/run "):
            task = cmd[len("/run "):].strip()
            agent.reset_memory()
            with console.status("[cyan]规划中...[/cyan]"):
                steps = planner.decompose(task)
            if not steps:
                console.print("[yellow]未能分解任务，尝试直接执行[/yellow]")
                with console.status("[cyan]Agent 执行中...[/cyan]"):
                    result = agent.run(task)
                console.print(Panel(Markdown(result), title="[bold blue]Agent[/bold blue]", border_style="blue"))
                continue

            # Todo 表格
            todo_table = Table(title=f"任务进度: {task[:30]}...", border_style="cyan")
            todo_table.add_column("#", style="dim")
            todo_table.add_column("步骤")
            todo_table.add_column("状态")
            todo_data = [(str(i), step, "⏳") for i, step in enumerate(steps, 1)]
            for row in todo_data:
                todo_table.add_row(*row)
            console.print(todo_table)
            console.print()

            final_parts = []
            for i, step in enumerate(steps, 1):
                console.print(f"[dim][Step {i}/{len(steps)}][/dim] [cyan]{step}[/cyan]")
                with console.status(f"[cyan]执行 Step {i}...[/cyan]"):
                    result = agent.run(step)

                # 更新 Todo 状态
                todo_data[i-1] = (str(i), step, "[green]✓[/green]")
                todo_table = Table(title=f"任务进度: {task[:30]}...", border_style="cyan")
                todo_table.add_column("#", style="dim")
                todo_table.add_column("步骤")
                todo_table.add_column("状态")
                for row in todo_data:
                    todo_table.add_row(*row)
                console.print(todo_table)

                final_parts.append(f"### Step {i}: {step}\n\n{result}")
                console.print(Markdown(f"**结果:** {result[:200]}{'...' if len(result) > 200 else ''}"))
                console.print()
                # 保留上下文，不 reset

            # 汇总
            summary_prompt = f"用户原始任务：{task}\n\n以下是各步骤执行结果，请汇总成最终答案：\n\n" + "\n\n".join(final_parts)
            with console.status("[cyan]汇总中...[/cyan]"):
                summary = agent.run(summary_prompt)
            console.print(Panel(Markdown(summary), title="[bold green]最终汇总[/bold green]", border_style="green"))
            console.print("[dim]各步骤详情:[/dim]")
            console.print(Markdown("\n---\n".join(final_parts)))
            continue

        # /remember 命令：存入长期记忆
        if cmd.startswith("/remember "):
            parts = cmd[len("/remember "):].strip().split(maxsplit=1)
            if len(parts) < 2:
                console.print("[yellow]用法: /remember <键> <内容>[/yellow]")
                continue
            key, content = parts
            vm.remember(key, content)
            console.print(f"[green]已记住: {key}[/green]")
            continue

        # /recall 命令：语义检索长期记忆
        if cmd.startswith("/recall "):
            query = cmd[len("/recall "):].strip()
            results = vm.recall(query)
            if results:
                table = Table(title=f"记忆检索: {query}", border_style="cyan")
                table.add_column("键", style="green")
                table.add_column("内容")
                table.add_column("相关度", style="dim")
                for r in results:
                    table.add_row(r["key"], r["content"][:80], f"{1-r['distance']:.3f}")
                console.print(table)
            else:
                console.print("[yellow]未找到相关记忆[/yellow]")
            continue

        # /compress 命令：压缩对话历史
        if cmd.strip() == "/compress":
            with console.status("[cyan]压缩中...[/cyan]"):
                summary = agent.compress_history()
            console.print(f"[green]已压缩：{summary[:200]}...[/green]")
            continue

        # /usage 命令：显示当前统计
        if cmd.strip() == "/usage":
            s = agent.stats
            table = Table(title="会话统计", border_style="cyan")
            table.add_column("指标", style="dim")
            table.add_column("值")
            table.add_row("工具调用", str(s["tool_calls"]))
            table.add_row("思考步数", str(s["steps"]))
            console.print(table)
            continue

        # /sessions 命令：列出历史会话
        if cmd.strip() == "/sessions":
            sessions = list_sessions()
            if sessions:
                table = Table(title="历史会话", border_style="cyan")
                table.add_column("ID", style="dim")
                table.add_column("标题")
                table.add_column("工具调用", style="dim")
                for s in sessions:
                    table.add_row(s["id"], s["title"], str(s["tool_calls"]))
                console.print(table)
            else:
                console.print("[yellow]暂无历史会话[/yellow]")
            continue

        # /skills 命令：列出可用技能
        if cmd.strip() == "/skills":
            skills = list_skills()
            if skills:
                table = Table(title="可用技能", border_style="cyan")
                table.add_column("名称", style="green")
                table.add_column("描述")
                table.add_column("步骤", style="dim")
                for s in skills:
                    table.add_row(s["name"], s["description"], str(s["steps"]))
                console.print(table)
            else:
                console.print("[yellow]暂无已保存的技能[/yellow]")
            continue

        # /learn 命令：从对话中学习技能
        if cmd.startswith("/learn "):
            topic = cmd[len("/learn "):].strip()
            with console.status("[cyan]学习中...[/cyan]"):
                result = learn_skill(agent, topic)
            console.print(f"[green]{result}[/green]")
            continue

        # /cron 命令：定时任务管理
        if cmd.startswith("/cron "):
            parts = cmd[len("/cron "):].strip().split(maxsplit=2)
            action = parts[0] if parts else ""
            if action == "add" and len(parts) >= 3:
                job_id = cron.add_job(parts[1], parts[2])
                console.print(f"[green]已创建定时任务: {job_id}[/green]")
            elif action == "list":
                jobs = cron.list_jobs()
                if jobs:
                    table = Table(title="定时任务", border_style="cyan")
                    table.add_column("ID", style="dim")
                    table.add_column("调度")
                    table.add_column("任务")
                    table.add_column("状态")
                    for j in jobs:
                        status = "⏸ 暂停" if j["paused"] else "▶ 运行"
                        table.add_row(j["id"], j["schedule"], j["task"][:30], status)
                    console.print(table)
                else:
                    console.print("[yellow]暂无定时任务[/yellow]")
            elif action == "remove" and len(parts) >= 2:
                ok = cron.remove_job(parts[1])
                console.print(f"[green]已删除[/green]" if ok else "[red]未找到该任务[/red]")
            elif action == "pause" and len(parts) >= 2:
                cron.pause_job(parts[1])
                console.print("[green]已暂停[/green]")
            elif action == "resume" and len(parts) >= 2:
                cron.resume_job(parts[1])
                console.print("[green]已恢复[/green]")
            elif action == "tick":
                results = cron.tick()
                console.print(f"[green]执行了 {len(results)} 个到期任务[/green]")
            else:
                console.print("[yellow]用法: /cron add <schedule> <任务> | list | remove <id> | pause <id> | resume <id>[/yellow]")
            continue

        # /search 命令：FTS5 全文搜索历史会话
        if cmd.startswith("/search "):
            query = cmd[len("/search "):].strip()
            results = search_sessions(query)
            if results:
                table = Table(title=f"搜索: {query}", border_style="cyan")
                table.add_column("ID", style="dim")
                table.add_column("标题")
                table.add_column("工具调用")
                for s in results:
                    table.add_row(s["id"], s["title"], str(s["tool_calls"]))
                console.print(table)
            else:
                console.print("[yellow]未找到匹配的会话[/yellow]")
            continue

        # /delegate 命令：创建子代理执行任务
        if cmd.startswith("/delegate "):
            task = cmd[len("/delegate "):].strip()
            with console.status("[cyan]子代理执行中...[/cyan]"):
                # 子代理：独立记忆，共享工具
                sub = Agent(llm=agent.llm, tool_registry=agent.tools)
                sub.reset_memory()
                result = sub.run(task)
                console.print(Panel(Markdown(result), title="[bold magenta]子代理[/bold magenta]", border_style="magenta"))
            continue

        # Phase 5: /batch 命令 — 顺序处理多个任务
        if cmd.startswith("/batch "):
            tasks = [t.strip() for t in cmd[len("/batch "):].strip().split("|") if t.strip()]
            if not tasks:
                console.print("[yellow]用法: /batch <任务1> | <任务2> | ...[/yellow]")
                continue
            table = Table(title="批量执行", border_style="cyan")
            table.add_column("#", style="dim")
            table.add_column("任务")
            table.add_column("结果")
            for i, t in enumerate(tasks, 1):
                agent.reset_memory()
                with console.status(f"[cyan]Batch {i}/{len(tasks)}...[/cyan]"):
                    r = agent.chat(t)
                table.add_row(str(i), t[:30], r[:60])
            console.print(table)
            continue

        # Phase 6: /export 命令 — 导出会话 JSONL
        if cmd.startswith("/export"):
            sid = cmd[len("/export "):].strip() if len(cmd) > len("/export") else "last"
            from src.core.session import load_session
            import json, os
            if sid == "last":
                sessions = list_sessions()
                sid = sessions[0]["id"] if sessions else None
            if not sid:
                console.print("[yellow]没有可导出会话[/yellow]")
                continue
            session = load_session(sid)
            if session:
                path = f"data/exports/session_{sid}.jsonl"
                os.makedirs("data/exports", exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    for m in session["messages"]:
                        f.write(json.dumps(m, ensure_ascii=False) + "\n")
                console.print(f"[green]已导出到 {path} ({len(session['messages'])} 条消息)[/green]")
            else:
                console.print("[yellow]会话不存在[/yellow]")
            continue

        # Phase 8: /mcp 命令 — MCP 服务器管理
        if cmd.startswith("/mcp "):
            parts = cmd[len("/mcp "):].strip().split(maxsplit=2)
            action = parts[0] if parts else ""
            if action == "connect" and len(parts) >= 3:
                ok = connect_mcp(parts[1], parts[2])
                console.print(f"[green]已连接 {parts[1]}[/green]" if ok else f"[red]连接失败[/red]")
            elif action == "list":
                servers = list_mcp()
                if servers:
                    table = Table(title="MCP 服务器", border_style="cyan")
                    table.add_column("名称")
                    table.add_column("工具数")
                    for s in servers:
                        table.add_row(s["name"], str(s["tools"]))
                    console.print(table)
                else:
                    console.print("[yellow]无已连接 MCP 服务器[/yellow]")
            else:
                console.print("[yellow]用法: /mcp connect <name> <command> | list[/yellow]")
            continue

        # Phase 3: /hook 命令 — 钩子系统
        if cmd.startswith("/hook "):
            parts = cmd[len("/hook "):].strip().split(maxsplit=2)
            action = parts[0] if parts else ""
            if action == "add" and len(parts) >= 3:
                event, command_line = parts[1], parts[2]
                if event in _hooks:
                    _hooks[event].append(command_line)
                    console.print(f"[green]已注册 {event} → {command_line}[/green]")
                else:
                    console.print(f"[yellow]无效事件: {event}，可用: {', '.join(_hooks.keys())}[/yellow]")
            elif action == "list":
                table = Table(title="已注册 Hooks", border_style="cyan")
                table.add_column("事件")
                table.add_column("命令")
                for event, cmds in _hooks.items():
                    for c in cmds:
                        table.add_row(event, c)
                console.print(table)
            else:
                console.print("[yellow]用法: /hook add <event> <command> | list[/yellow]")
            continue

        # /consolidate 命令：总结当前对话并存入长期记忆
        if cmd.strip() == "/consolidate":
            with console.status("[cyan]巩固记忆...[/cyan]"):
                summary = agent.compress_history()
                try:
                    vm.remember(f"consolidated_{int(time.time())}", summary)
                    console.print(f"[green]已巩固记忆[/green]")
                except Exception:
                    console.print("[yellow]长期记忆不可用，仅显示摘要[/yellow]")
                    console.print(summary[:300])
            continue

        # 普通对话
        with console.status("[cyan]Agent 思考中...[/cyan]"):
            result = agent.run(cmd)
        console.print(Panel(
            Markdown(result),
            title="[bold blue]Agent[/bold blue]",
            border_style="blue"
        ))


if __name__ == "__main__":
    main()
