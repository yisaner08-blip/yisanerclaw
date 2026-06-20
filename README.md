# AI Agent — ReAct 模式工具调用型智能助手

基于 React（Reasoning + Acting）模式实现的 AI Agent，使用 DeepSeek API，支持多种工具调用。

## 架构

```
CLI (main.py)
  ├── Agent (ReAct 循环)
  │     ├── LLM (DeepSeek API)
  │     ├── ConversationMemory (短期对话记忆)
  │     └── ToolRegistry (工具注册表)
  ├── Planner (/plan /run 任务分解)
  └── VectorMemory (/remember /recall 长期语义记忆)

工具:
  src/tools/
    ├── calculator.py    — 安全数学计算
    ├── file_ops.py      — 文件读写、目录列表
    └── web_search.py    — DuckDuckGo 网页搜索
```

## 快速开始

```bash
cd agent_project
cp .env.example .env        # 填入你的 API Key
./venv/bin/pip install -r requirements.txt
./venv/bin/python3 -m src.cli.main
```

## CLI 命令

| 命令 | 功能 |
|------|------|
| 直接输入问题 | Agent 自动调用工具回答 |
| `/plan <任务>` | 将任务分解为步骤 |
| `/run <任务>` | 分解任务后逐步执行并汇总 |
| `/remember <键> <内容>` | 存入长期语义记忆 |
| `/recall <查询>` | 语义检索长期记忆 |
| `reset` | 清除短期对话记忆 |
| `退出` / `exit` / `q` | 退出程序 |

## 配置 (.env)

```env
OPENAI_API_KEY=sk-xxx              # DeepSeek API Key
OPENAI_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-v4-flash        # 上下文 1M
```

## 依赖

- `openai` — API 调用
- `pydantic` — 数据模型
- `rich` — CLI 美化
- `python-dotenv` — 环境变量
- `ddgs` — DuckDuckGo 搜索
- `chromadb` + `sentence-transformers` — 长期向量记忆
- `torch` — 嵌入模型推理
