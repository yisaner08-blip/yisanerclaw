# yisanerclaw — AI Agent 项目规则

## 项目概览

基于 ReAct 模式的 AI Agent，使用 DeepSeek API，支持 8 个工具。
项目处于活跃开发阶段，功能持续迭代中。

## 技术栈

- Python 3.12，虚拟环境 `agent_project/venv/`
- LLM：DeepSeek v4-flash（OpenAI 兼容 API）
- 依赖见 `requirements.txt`

## 项目结构

```
agent_project/
├── src/core/     — LLM、Agent、工具系统、记忆模块
├── src/tools/    — 具体工具实现（calculator, shell, web 等）
├── src/cli/      — CLI 交互界面
├── docs/         — 设计文档
├── tests/        — 测试（待补充）
├── data/         — ChromaDB 持久化（不提交）
└── venv/         — Python 虚拟环境（不提交）
```

## 环境约束

- **无 sudo 权限**，不能安装系统包
- **代理端口 7897**：`export http_proxy=http://127.0.0.1:7897`（按需使用）
- **国内网络**：PyPI 用阿里云镜像 `https://mirrors.aliyun.com/pypi/simple/`
- **HuggingFace**：用 `hf-mirror.com` 镜像（VectorMemory 已预设）
- **GitHub SSH**：已配置 Ed25519 密钥

## 常用命令

```bash
# 安装依赖（有代理时）
./venv/bin/pip install <package> --proxy http://127.0.0.1:7897

# 安装依赖（直连阿里云）
./venv/bin/pip install <package> -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# 启动 Agent CLI
cd agent_project && ./venv/bin/python3 -m src.cli.main

# 快速测试
./venv/bin/python3 -c "from src.cli.main import create_agent; print(create_agent().run('计算 1+1'))"

# Git 推送
cd agent_project && git push
```

## 编码规范

### 文件大小
- 单个 Python 文件 ≤ 300 行
- 每层文件夹 ≤ 8 个文件

### 命名规范
- 文件名：snake_case（`file_ops.py`, `web_search.py`）
- 类名：PascalCase（`ToolRegistry`, `ConversationMemory`）
- 函数/变量：snake_case（`run_shell`, `max_steps`）

### 注释规范
- 模块级 docstring 说明用途
- 复杂逻辑加行内注释
- 工具函数有参数说明

### 错误处理
- 工具函数返回错误字符串，不抛异常
- `except Exception` 只在明确需要兜底时使用
- 关键路径加 try/except

## 工具开发规范

新增工具需遵循：
1. 在 `src/tools/` 创建文件
2. 函数名用 `snake_case`
3. 返回 `str` 类型（成功或错误信息）
4. 在 `src/cli/main.py` 的 `create_agent()` 中注册
5. 添加 JSON Schema 参数定义

## 安全规则

- `.env` 文件绝不提交 Git
- API Key 不硬编码在代码中
- Shell 工具已内置危险命令过滤
- 文件操作限制在 workspace 内
