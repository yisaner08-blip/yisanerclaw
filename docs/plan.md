# AI Agent —— 从零实现工具调用型 Agent 详细方案

---

## 前言：先理解 Agent 到底在做什么

在你写第一行代码之前，理解这个概念最重要：

```
普通 LLM：你问 "今天几号" → 它答 "抱歉我的知识截止到..."
Agent：  你问 "今天几号" → 它发现需要调用 get_current_date() → 执行工具 → 告诉你结果
```

**Agent = LLM + 工具 + 循环**。LLM 是大脑，工具是手，循环是"思考→行动→观察"的反复。

**你最终会看到的效果**：

```
你: 帮我创建一个文件夹叫 test，在里面新建一个 hello.txt，写上今天的日期

Agent 的思考过程:
  〇 思考: 我需要先获取今天的日期，然后再创建文件夹和文件
  ⚡ 动作: 调用 get_current_date() → 结果: "2026-06-13"
  〇 思考: 已获取日期，现在创建 test 文件夹
  ⚡ 动作: 调用 create_directory(path="test") → 结果: 成功
  〇 思考: 文件夹已创建，现在写入文件
  ⚡ 动作: 调用 write_file(path="test/hello.txt", content="2026-06-13") → 结果: 成功
  
Agent: 已完成！在 test/hello.txt 中写入了日期 2026-06-13
```

这就是你要实现的东西。

---

## Phase 0：环境准备（10 分钟）

### 你需要什么

1. **OpenAI API Key**：去 https://platform.openai.com 注册，充值 $5（够你开发用了）
2. **Python 3.10+**：你系统上应该已经有

### 创建项目

```bash
# 在你的工作目录下
mkdir agent_project
cd agent_project

# 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate

# 创建基础文件
touch requirements.txt
```

**requirements.txt 内容**（Phase 1 只需要这些）：
```
openai>=1.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
rich>=13.0.0
```

```bash
pip install -r requirements.txt
```

### 创建 API Key 配置文件

在项目根目录创建 `.env` 文件：
```
OPENAI_API_KEY=sk-你的key
OPENAI_BASE_URL=https://api.deepseek.com/v1  # 如果你用 DeepSeek（国内更方便）
```

> **省钱提示**：DeepSeek API 比 OpenAI 便宜 10 倍，效果接近。去 https://platform.deepseek.com 注册即可。代码完全兼容 OpenAI 格式。

---

## Phase 1：一步一步搭积木

### 总体执行顺序

```
文件 1: src/core/llm.py        ← 让 LLM 能说话
文件 2: src/core/tool.py       ← 创建工具系统
文件 3: src/core/agent.py      ← 把 LLM 和工具串起来（ReAct 循环）
文件 4: src/tools/calculator.py ← 写第一个工具
文件 5: src/cli/main.py        ← 交互界面
```

每写完一个文件就测试一下，不要把 5 个文件全写了再测。现在开始。

---

### 文件 1：`src/core/llm.py` —— LLM 调用封装

**这个文件做什么**：让代码能调用大模型。把 API key、消息发送、结果接收封装成一个简单的类。

**你需要知道的 API 概念**：

```
调用 LLM 就像发一条微信：
  你发送: [系统提示, 历史对话, 当前问题]
  LLM返回: 一段文本回复
```

**具体实现的类和方法**（让 AI 帮你写这个文件的代码）：

```python
class LLM:
    """
    封装大模型调用
    
    核心方法只有一个：chat(messages) → str
    - 输入：messages 是一个列表，每项是 {"role": "...", "content": "..."}
    - 输出：LLM 的回复文本
    
    messages 的 role 有三种：
    - "system"：系统提示词，告诉 LLM 它是什么角色
    - "user"：用户说的话
    - "assistant"：LLM 自己说的话
    - "tool"：工具返回的结果（后面会用到）
    """
    
    def __init__(self, model="deepseek-chat", api_key=None, base_url=None):
        """
        初始化 LLM 客户端。
        - 读取 .env 里的 API key
        - 设置模型名称
        """
        pass
    
    def chat(self, messages: list[dict], temperature=0.0) -> str:
        """
        发送消息给 LLM，返回回复文本。
        temperature=0 表示让 LLM 尽量确定性地回答（不要创意）。
        """
        pass
```

**实现要点**（你可以直接把下面这段话喂给 AI 让它写）：

> "用 openai 库写一个 LLM 类，调用 OpenAI-compatible 的 API。构造函数接收 model、api_key、base_url 参数。chat 方法接收 messages 列表（格式：[{"role": "系统/user/assistant", "content": "..."}]），返回 LLM 的回复文本。用 python-dotenv 从 .env 文件读取 OPENAI_API_KEY 和 OPENAI_BASE_URL 作为默认值。"

**测试这个文件**（写完后在项目根目录执行）：

```python
# 在 Python 终端测试
from src.core.llm import LLM
llm = LLM()
response = llm.chat([{"role": "user", "content": "你好，请用一句话介绍你自己"}])
print(response)
# 应该输出类似: "你好！我是一个AI助手..."
```

**你要理解的部分**（不需要背，但要知道发生什么）：
- `messages` 列表的每一轮对话是一条记录
- `role` 标识谁说的话
- `temperature` 控制随机性

---

### 文件 2：`src/core/tool.py` —— 工具系统

**这个文件做什么**：定义"工具"是什么，让 Agent 知道有哪些工具可用，并能执行工具。

**核心概念**——一个工具由四样东西组成：

```
工具 = {
    name: "calculator",           # 工具名，LLM 用这个名字来调用
    description: "计算数学表达式",  # 描述，LLM 看这个来决定要不要用
    parameters: {                 # 参数列表，告诉 LLM 要传什么
        "expression": {
            "type": "string",
            "description": "数学表达式"
        }
    },
    function: calculator_func     # 实际执行的 Python 函数
}
```

**你需要定义的数据结构**：

```python
class Tool:
    """单个工具的定义"""
    name: str              # 工具名称，如 "calculator"
    description: str       # 工具描述，如 "计算数学表达式"
    parameters: dict       # 参数 JSON Schema，如 {"expression": {"type": "string", ...}}
    function: callable     # 实际执行的 Python 函数

class ToolRegistry:
    """
    工具注册表。管理所有可用工具。
    
    核心方法：
    - register(tool): 注册一个工具
    - get(name): 获取一个工具
    - list_all(): 获取所有工具列表
    - to_openai_format(): 把工具转换成 OpenAI function calling 格式
    """
    pass
```

**`to_openai_format()` 很重要**——你需要把工具信息转成 LLM 能理解的格式：

```python
def to_openai_format(self) -> list[dict]:
    """
    返回：
    [
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "计算数学表达式",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式，如 2+3*4"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    ]
    """
```

**实现要点**（让 AI 写这个文件的代码）：

> "写一个 Tool 类和一个 ToolRegistry 类。Tool 类用 pydantic BaseModel，有 name、description、parameters、function 字段。ToolRegistry 用字典存储工具（name → Tool），提供 register、get、list_all、to_openai_format 方法。to_openai_format 返回 OpenAI function calling 兼容的格式。"

**测试这个文件**：

```python
from src.core.tool import Tool, ToolRegistry

# 定义工具函数
def greet(name: str) -> str:
    return f"你好，{name}！"

# 创建工具
tool = Tool(
    name="greet",
    description="向某人问好",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "要问好的人的名字"}
        },
        "required": ["name"]
    },
    function=greet
)

# 注册
registry = ToolRegistry()
registry.register(tool)

# 测试执行
result = registry.execute("greet", {"name": "小明"})
print(result)  # 应该输出: "你好，小明！"

# 测试 OpenAI 格式
print(registry.to_openai_format())
# 输出应该和上面展示的格式一样
```

---

### 文件 3：`src/core/agent.py` —— ReAct 循环

**这是整个项目的心脏！** 这个文件你需要自己理解并手写核心逻辑。

#### 先理解 ReAct 循环是什么

ReAct = **Re**asoning（推理） + **Act**ing（行动）。每次循环：

```
Step 1: 把当前状态发给 LLM
        状态包括：系统提示词 + 对话历史 + 用户问题 + (工具调用结果)

Step 2: LLM 返回回复
        回复可能是：
        - 一段普通文本（"答案是 42"）
        - 或者一个"function call"（告诉你要调用哪个工具、传什么参数）

Step 3: 判断
        - 如果 LLM 返回了 function call → 执行工具，把结果加回对话历史，回到 Step 1
        - 如果 LLM 返回了普通文本 → 这就是最终答案，结束
```

#### 用伪代码描述

```python
class Agent:
    def __init__(self, llm, tool_registry, system_prompt=None):
        """初始化 Agent：传入 LLM、工具注册表、系统提示词"""
        pass
    
    def run(self, user_input: str) -> str:
        """
        执行一次 Agent 对话。这是最核心的方法。
        """
        # 1. 初始化消息列表（对话上下文）
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_input}
        ]
        
        # 2. 开始 ReAct 循环
        max_steps = 10  # 防止无限循环，最多 10 轮
        for step in range(max_steps):
            # 调用 LLM（传入 tools 定义，让 LLM 知道可以调用哪些工具）
            response = self.llm.chat(messages, tools=self.tools.to_openai_format())
            
            # 3. 解析 LLM 的回复
            if 回复中包含 function_call:
                # 4. 执行工具
                tool_name = 从回复中提取工具名
                tool_args = 从回复中提取参数
                tool_result = self.tools.execute(tool_name, tool_args)
                
                # 5. 把工具调用和结果追加到消息历史
                messages.append(LLM的回复消息)        # role: assistant, 带 function_call
                messages.append(tool_result消息)       # role: tool, 带结果
                
                # 循环继续，LLM 会在下一轮看到工具结果
                
            else:
                # 6. LLM 没有调用工具，说明它觉得任务完成了
                # 返回最后的文本回复
                return response 的内容
        
        # 7. 如果超过了最大步数还没结束
        return "Agent 执行超过最大步数，任务中断。"
    
    def _build_system_prompt(self) -> str:
        """构造系统提示词，告诉 LLM 它是 Agent，可以使用工具"""
        return (
            "你是一个智能助手，可以使用以下工具来完成任务。"
            "当需要获取信息或执行操作时，请使用合适的工具。"
            "当你已经完成任务时，直接给出最终答案。"
        )
```

#### 关键实现细节

**1. 调用 LLM 时怎么传 tools**

你用的是 OpenAI-compatible API，不需要自己解析 function call。直接按 OpenAI 的格式调用：

```python
# 调用 LLM 的代码（在 Agent.run 里）
from openai import OpenAI

client = OpenAI(
    api_key="...",
    base_url="..."
)

response = client.chat.completions.create(
    model="deepseek-chat",  # 或 "gpt-4o"
    messages=messages,
    tools=self.tools.to_openai_format(),  # ← 传入工具定义
    temperature=0
)

# 获取 LLM 的回复
choice = response.choices[0]
message = choice.message

if message.tool_calls:  # LLM 想调用工具
    for tool_call in message.tool_calls:
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        # 执行工具...
else:  # LLM 给了文本回复
    return message.content
```

**2. 消息历史怎么拼接**

当 LLM 调用工具后，你需要追加两条消息到 messages 列表中：

```python
# LLM 返回后，messages 增加：

# 第 1 条：LLM 的助手消息（包含 function_call）
messages.append({
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "call_xxx",
            "type": "function",
            "function": {
                "name": "calculator",
                "arguments": '{"expression": "2+2"}'
            }
        }
    ]
})

# 第 2 条：工具执行结果
messages.append({
    "role": "tool",
    "tool_call_id": "call_xxx",
    "content": "4"  # 工具返回的结果
})
```

> **这个拼接逻辑是核心，必须亲手写。** 你可以让 AI 解释每行代码，但结构要自己理解。

#### 思维跟踪：举一个完整的例子

用户问："计算 (123 + 456) * 789 等于多少？"

```
【第 1 轮】
messages = [
    system: "你是一个智能助手，可以使用工具..."
    user:   "计算 (123 + 456) * 789 等于多少？"
]
→ 发给 LLM
→ LLM 回复: tool_calls = [{name: "calculator", arguments: "(123+456)*789"}]

→ 执行 calculator("(123+456)*789")
→ 结果: "456831"

→ messages 变成:
    system: "你是一个智能助手..."
    user:   "计算 (123 + 456) * 789"
    assistant: [tool_call: calculator, "(123+456)*789"]
    tool:   "456831"

【第 2 轮】
→ 发给 LLM（这次 messages 多了两条）
→ LLM 看到 tool 返回了 456831
→ LLM 回复: content = "计算结果是 456831"
→ 没有 tool_calls，循环结束！
→ 输出给用户: "计算结果是 456831"
```

**你看懂了这个流程，ReAct 循环就会写了。**

#### 测试 Agent

```python
from src.core.llm import LLM
from src.core.tool import Tool, ToolRegistry
from src.core.agent import Agent

# 准备
llm = LLM()

def calculator(expression: str) -> str:
    return str(eval(expression))

registry = ToolRegistry()
registry.register(Tool(
    name="calculator",
    description="计算数学表达式",
    parameters={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "数学表达式"}
        },
        "required": ["expression"]
    },
    function=calculator
))

# 运行 Agent
agent = Agent(llm=llm, tool_registry=registry)
result = agent.run("计算 (123 + 456) * 789 等于多少？")
print(result)
# 期望输出: 456831
```

---

### 文件 4：`src/tools/calculator.py` —— 计算器工具

**这个文件做什么**：定义计算器工具的具体实现。

**关键点**：**不要用 raw eval，安全第一。**

```python
import math

def calculator(expression: str) -> str:
    """
    安全地计算数学表达式。
    只允许数字、运算符和 math 函数，禁止任意代码执行。
    """
    # 只允许：数字、运算符、括号、空格、小数点、math 模块的函数
    allowed_names = {"__builtins__": None}
    allowed_names.update({
        "abs": abs, "round": round, "min": min, "max": max,
        "pow": pow, "math": math
    })
    
    try:
        # 先检查表达式是否只包含允许的字符
        import re
        if not re.match(r'^[\d\s\+\-\*\/\(\)\.\,\%\^a-zA-Z_]+$', expression):
            return f"错误：表达式包含不允许的字符"
        
        result = eval(expression, allowed_names)
        return str(result)
    except Exception as e:
        return f"错误：{e}"
```

**让 AI 帮你**：这个文件直接让 AI 写就行，告诉它"写一个安全的数学表达式计算函数，限制 eval 的命名空间，只允许数字运算符和 math 模块"。

---

### 文件 5：`src/cli/main.py` —— 交互界面

**这个文件做什么**：让你在终端里和 Agent 对话。

```python
def main():
    # 1. 初始化 LLM、工具注册表、Agent
    llm = LLM()
    registry = ToolRegistry()
    # 注册工具...
    agent = Agent(llm=llm, tool_registry=registry)
    
    # 2. 交互循环
    while True:
        user_input = input("你: ")
        if user_input in ("退出", "exit", "quit"):
            break
        result = agent.run(user_input)
        print(f"Agent: {result}")
```

**让 AI 帮你**：这个太简单，直接让 AI 写，你用 `rich` 库美化一下输出也行。

---

## Phase 1 完成检查清单

跑完 Phase 1 后，你应该能：

- [ ] 在终端里输入问题，LLM 能回答
- [ ] 在终端里输入"计算 1+2"，Agent 会自动调用 calculator 工具并返回 "3"
- [ ] 理解 messages 列表在每一轮是怎么变化的
- [ ] 理解 LLM 返回 function_call 后你是怎么处理的

---

## Phase 2：增加记忆 + 更多工具

### 文件 6：`src/core/memory.py` —— 记忆模块

**为什么需要记忆**：现在你的 Agent 每次对话都是"健忘症"，说完就忘。你需要让它记住之前的对话。

**两级记忆设计**：

```
短期记忆（ConversationMemory）
  └─ 存最近 N 轮对话，像滑动窗口
  └─ 当对话太长时，自动抛弃最早的消息
  └─ 实现：直接维护一个 messages 列表，超长了就裁剪

长期记忆（VectorMemory）—— Phase 3 再做
  └─ 把重要信息向量化存到数据库
  └─ 以后对话时可以检索
  └─ 实现：embeddings + chromadb/faiss
```

**短期记忆实现**（自己手写）：

```python
class ConversationMemory:
    """
    短期记忆：管理对话上下文窗口。
    
    核心思想：
    - 维护 messages 列表
    - 当列表过长，保留 system 消息 + 最近 N 轮对话
    """
    
    def __init__(self, max_turns=20):
        """
        max_turns: 最多保留多少轮对话（每轮 = user + assistant 共 2 条）
        """
        self.max_turns = max_turns
        self.system_message = None  # 保留 system 消息
        self.turns = []  # [(user_msg, assistant_msg), ...]
    
    def add_user_message(self, message):
        """添加用户消息"""
        self.turns.append({"role": "user", "content": message})
    
    def add_assistant_message(self, message):
        """添加助手消息"""
        if self.turns:
            self.turns[-1]["assistant"] = message
    
    def to_messages(self) -> list[dict]:
        """把所有记忆拼成 messages 列表"""
        messages = []
        if self.system_message:
            messages.append(self.system_message)
        
        # 只保留最近 max_turns 轮
        recent = self.turns[-self.max_turns:]
        for turn in recent:
            messages.append({"role": "user", "content": turn["user"]})
            if turn.get("assistant"):
                messages.append(turn["assistant"])  # 可能含 tool_calls
        
        return messages
```

**怎么用**：修改 Agent.run，不直接用列表存 messages，而是用 ConversationMemory。

---

### 文件 7：`src/tools/file_ops.py` —— 文件操作工具

让 Agent 能读写文件、创建目录。**安全第一，限制操作路径。**

```python
def read_file(filepath: str) -> str:
    """读取文件内容"""
    # 确保路径在允许的目录内
    pass

def write_file(filepath: str, content: str) -> str:
    """写入文件"""
    pass

def list_directory(path: str) -> str:
    """列出目录内容"""
    pass
```

**让 AI 写**这个文件，但你要告诉它"只能在项目目录内操作，禁止访问其他路径"。

---

### 文件 8：`src/tools/web_search.py` —— 网页搜索

用 DuckDuckGo 的免费搜索 API（不需要 API key）：

```bash
pip install duckduckgo-search
```

**让 AI 写**这个文件，告诉它"用 duckduckgo_search 库实现一个 search 功能，接收 query，返回前 5 条结果的标题和链接"。

---

### Phase 2 完成检查清单

- [ ] Agent 能在多轮对话中记住上下文
- [ ] Agent 能读写文件、创建目录
- [ ] Agent 能搜索网页

---

## Phase 3：高级功能（理解比实现重要）

### 任务规划器（Planner）

**做什么**：当你问"帮我写一篇关于 AI Agent 的文章，然后保存为 agen.txt"，Agent 需要自己分解：

```
任务分解:
  Step 1: 搜索"AI Agent 最新发展"
  Step 2: 基于搜索结果，写文章大纲
  Step 3: 逐段写文章
  Step 4: 保存到 agent.txt
```

**实现思路**（这也让 AI 帮你写结构，但你理解逻辑）：

```python
class Planner:
    def decompose(self, task: str) -> list[str]:
        """
        向 LLM 发送任务，让它拆成子任务列表。
        提示词模板：
        "把以下任务分解为子任务步骤，每步一行，按执行顺序排列：
        任务：{task}"
        """
        pass
```

---

### 长期记忆（VectorMemory）

**做什么**：把重要信息存到向量数据库，以后能"想起来"。

**需要装**：
```bash
pip install chromadb sentence-transformers
```

**但这一步不是必须的**——你先做到 Phase 2，Phase 3 之后再慢慢加。向量数据库的概念你可以边做边学。

---

## 你该怎么开始

```
第一步（现在）：
  1. 创建项目文件夹
  2. 装依赖
  3. 配置 API Key
  
第二步（第一个文件）：
  1. 写 src/core/llm.py（让 AI 写，你测试）
  2. 确认 LLM 能调用成功
  
第三步（第二个文件）：
  1. 写 src/core/tool.py（让 AI 写，你测试）
  2. 确认 ToolRegistry 能注册、执行、导出 OpenAI 格式
  
第四步（第三个文件——核心）：
  1. 理解上面的 ReAct 循环例子（用户问计算题的完整 trace）
  2. 手写 src/core/agent.py
  3. 写一个简单的 calculator 工具
  4. 测试整个流程
  
第五步：
  1. 写 CLI 交互界面
  2. 恭喜，你的 Phase 1 完成了！
```

---

## 容易卡住的地方（提前告诉你）

### 1. API 调用失败

```
错误: Connection refused / 超时
解决: 检查 API key 是否正确，base_url 是否正确
如果用的是 DeepSeek，base_url 是 "https://api.deepseek.com"
```

### 2. LLM 回复格式不对

```
症状: LLM 没调用工具，直接说"我无法计算"
原因: 你传给 LLM 的 tool 定义格式不对，或者 system prompt 没说清楚
解决: 打印出 to_openai_format() 的结果，确认格式正确
```

### 3. 消息拼接错误

```
症状: LLM 好像"看不到"工具返回的结果
原因: tool 角色的消息没正确追加到 messages 列表
解决: 打印每轮的 messages 列表，确认结构正确
```

### 4. 无限循环

```
症状: Agent 一直调用工具，停不下来
解决: max_steps 限制，但这个只是兜底。
根本原因通常是:
  - 工具返回的结果对 LLM 没用
  - system prompt 里应该加一句"如果已有足够信息，直接回答"
```

---

## 关于 AI 的使用

| 让 AI 帮你写的 | 你自己手写的 |
|---|---|
| `llm.py` - API 封装 | `agent.py` - ReAct 循环逻辑 |
| `tool.py` - 工具系统框架 | 理解 messages 是如何拼接的 |
| 各种工具函数（calculator, file_ops 等） | 测试和调试整个流程 |
| CLI 界面 | tool_calls 的处理逻辑 |
| planner.py 框架 | 自己的 README 和文档 |
| 测试用例框架 | 分析 bug 和修改代码 |

**原则**：AI 写辅助性的、重复性的代码。核心的循环逻辑、数据流——你必须手写和理解。
