# 项目上下文

## 项目名称
yisanerclaw — 基于 ReAct 模式的 AI Agent

## 技术栈
- Python 3.12，虚拟环境 `venv/`
- LLM：DeepSeek v4-flash（OpenAI 兼容 API）
- 记忆：ConversationMemory（短期）+ VectorMemory ChromaDB（长期）
- 工具：calculator, file_ops, web_search, web_fetch, shell, system_info

## 项目结构
```
src/core/      — LLM、Agent、工具系统、记忆模块
src/tools/     — 具体工具实现
src/cli/       — CLI 交互界面
data/chroma/   — ChromaDB 持久化
```

## 启动方式
```bash
./venv/bin/python3 -m src.cli.main
```

## 环境约束
- 无 sudo 权限
- 代理端口 7897（按需使用）
- HuggingFace 使用 hf-mirror.com 镜像
