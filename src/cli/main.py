"""CLI 交互界面 —— 在终端里和 Agent 对话"""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from src.core.llm import LLM
from src.core.tool import Tool, ToolRegistry
from src.core.agent import Agent
from src.core.planner import Planner
from src.core.vector_memory import VectorMemory
from src.tools.calculator import calculator
from src.tools.file_ops import read_file, write_file, list_directory
from src.tools.web_search import web_search
from src.tools.web_fetch import web_fetch
from src.tools.shell import run_shell
from src.tools.system_info import get_current_time, get_environment


def create_agent(vm=None) -> Agent:
    llm = LLM()
    registry = ToolRegistry()

    registry.register(Tool(
        name="calculator",
        description="计算数学表达式，支持 +-*/%^ 和 math 函数",
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "数学表达式，如 '2+3*4' 或 'math.sqrt(100)'"}
            },
            "required": ["expression"]
        },
        function=calculator
    ))
    registry.register(Tool(
        name="read_file",
        description="读取文件内容",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "文件路径"}
            },
            "required": ["filepath"]
        },
        function=read_file
    ))
    registry.register(Tool(
        name="write_file",
        description="写入内容到文件，会自动创建父目录",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的内容"}
            },
            "required": ["filepath", "content"]
        },
        function=write_file
    ))
    registry.register(Tool(
        name="list_directory",
        description="列出目录内容",
        parameters={
            "type": "object",
            "properties": {
                "dirpath": {"type": "string", "description": "目录路径，默认当前目录", "default": "."}
            }
        },
        function=list_directory
    ))
    registry.register(Tool(
        name="web_search",
        description="搜索网页，返回前几条结果的标题、链接和摘要",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "max_results": {"type": "integer", "description": "最多返回几条结果", "default": 5}
            },
            "required": ["query"]
        },
        function=web_search
    ))

    # 注册 shell 执行工具
    registry.register(Tool(
        name="run_shell",
        description="执行 shell 命令并返回输出。可用于查看文件、运行脚本、查看系统信息等。禁止 sudo/rm -rf/reboot 等危险操作",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的 shell 命令，如 'ls -la' 或 'cat file.txt'"}
            },
            "required": ["command"]
        },
        function=run_shell
    ))

    # 注册网页抓取工具
    registry.register(Tool(
        name="web_fetch",
        description="抓取指定 URL 的网页内容，提取正文文本（去除 HTML 标签）",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要抓取的网页 URL"}
            },
            "required": ["url"]
        },
        function=web_fetch
    ))

    # 注册系统信息工具
    registry.register(Tool(
        name="get_current_time",
        description="获取当前日期和时间",
        parameters={"type": "object", "properties": {}},
        function=get_current_time
    ))
    registry.register(Tool(
        name="get_environment",
        description="获取系统环境信息：Python 版本、操作系统、工作目录",
        parameters={"type": "object", "properties": {}},
        function=get_environment
    ))

    return Agent(llm=llm, tool_registry=registry, vector_memory=vm)


def main():
    console = Console()
    console.print(Panel.fit(
        "[bold cyan]AI Agent[/bold cyan] — ReAct 模式 (8 工具)\n"
        "命令: [bold blue]/plan[/bold blue] 分解  [bold blue]/run[/bold blue] 分解执行  [bold blue]/todo[/bold blue] 任务状态\n"
        "      [bold blue]/remember[/bold blue] 长期记忆  [bold blue]/recall[/bold blue] 语义检索\n"
        "直接输入问题  Agent 自动调用工具回答\n"
        "[bold red]退出/exit/q[/bold red] 结束 | [bold yellow]reset[/bold yellow] 清除记忆",
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
                agent.reset_memory()

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
