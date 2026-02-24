# 金融分析 Multi-Agent 系统

> 项目已完整搭建。请直接阅读**快速开始**部分。

---

## 🚀 快速开始（5分钟）

### 前置条件
- ✅ 创建Python 3.10+ 虚拟环境
- ✅ 依赖包已安装（`requirements.txt`）
- ✅ `.env` 已配置

### 方式 1️⃣ : 交互式菜单（推荐新手）

```bash
# 激活环境
conda activate xxx

# 进入项目目录
cd 文件地址

# 运行交互模式
python main.py
```

**交互菜单**（Phase 3 支持会话管理）：
```
请选择操作:
  [1] 分析股票     ← 选择/创建会话 → 输入代码 → 分析
  [2] 查看历史报告 ← 浏览已生成的 MD/HTML/JSON 报告
  [3] 管理会话     ← 查看/删除分析会话  (Phase 3 NEW!)
  [q] 退出
```

**分析股票流程**：
1. 选择或创建会话（系统会记住历史分析）
2. 输入股票代码（如 `600519.SH`）
3. 选择时间范围（3/6/12/24 个月）
4. 选择输出格式（全部/HTML/Markdown/JSON）
5. 确认开始分析（系统自动注入历史上下文！）
6. 查看结果，自动打开 HTML 报告

### 方式 2️⃣ : 命令行快速模式

```bash
# 最简单：直接分析
python main.py 600519.SH

# 自定义请求
python main.py "分析 AAPL，给出 6 个月短期建议"
```

**输出**：
- 终端显示分析摘要（建议、目标价、止损、置信度等）
- 自动生成 3 种格式报告（Markdown + HTML + JSON）
- 询问是否在浏览器打开 HTML 报告

---

## 📊 生成的报告类型

### Markdown 报告 (`.md`)
- 📝 纯文本，易于版本控制和邮件分享
- 📋 完整的表格、列表、结论

### HTML 报告 (`.html`)
- 🎨 美观的交互式展示
- 📈 嵌入 matplotlib 技术指标图表
- 📱 响应式设计

### JSON 报告 (`.json`)
- ⚙️ 机器可读，便于二次处理
- 🔄 包含所有原始分析数据

**报告位置**：`reports/YYYY-MM-DD/{SYMBOL}/report_*.{md|html|json}`

---

## 🎯 支持的股票代码

| 市场 | 格式 | 示例 |
|------|------|------|
| A 股 | XXXXXX.SH / XXXXXX.SZ | 600519.SH（茅台） |
| 港股 | XXXX.HK | 0700.HK（腾讯） |
| 美股 | XXXX | AAPL（苹果） |

---

## ⚙️ 配置说明

### LLM 选择

编辑 `.env`，修改 `LLM_PROVIDER` 切换：

```bash
LLM_PROVIDER=kimi        
# LLM_PROVIDER=claude    
# LLM_PROVIDER=deepseek  
# LLM_PROVIDER=qwen     
```

### 时间参数调整

```bash
DATA_FETCH_TIMEOUT=60    # 数据获取超时（秒）
MAX_TOKENS=2000          # LLM 输出 Token 数
```

---

## 📂 完整项目结构

```
agent/
├── README.md                     ← 本文档
├── .env                          ← 配置（API keys）
├── .gitignore                    ← Git 忽略规则
├── requirements.txt              ← 依赖列表
├── agent.db                      ⭐ SQLite 数据库（Phase 3，自动创建）
│
├── config.py                     ← 多 LLM 配置工厂
├── state.py                      ← LangGraph 状态定义
├── graph.py                      ← 工作流编排
├── main.py                       ⭐ 入口（支持交互 + 命令行）
├── report_generator.py           ⭐ 报告生成（MD/HTML/JSON）
│
├── storage/                      ⭐ 存储层（Phase 3 新增）
│   ├── __init__.py
│   ├── database.py               ← SQLite 连接管理
│   ├── models.py                 ← SQLAlchemy ORM 数据模型
│   └── repositories.py          ← Repository 模式实现
│
├── services/                     ⭐ 服务层（Phase 3 新增）
│   ├── __init__.py
│   ├── session_manager.py        ← 会话生命周期管理
│   └── context_manager.py       ← 上下文窗口管理
│
├── tools/                        ← 数据和分析工具
│   ├── __init__.py
│   ├── data_tools.py            ← AkShare 数据获取
│   └── technical_tools.py       ← 技术指标计算
│
├── agents/                       ← 6 个专业 Agent
│   ├── __init__.py
│   ├── planner.py               ← 规划 Agent
│   ├── data_agent.py            ← 数据 Agent
│   ├── technical_agent.py       ← 技术分析 Agent
│   ├── fundamental_agent.py     ← 基本面分析 Agent
│   ├── reviewer.py              ← 评审 Agent
│   └── decider.py               ← 决策 Agent
│
├── cli/                         ⭐ 交互式 CLI
│   ├── __init__.py
│   └── interactive.py           ← 菜单系统（支持会话管理）
│
└── reports/                     ← 生成的报告（自动创建）
    └── YYYY-MM-DD/
        └── {SYMBOL}/
            ├── report_*.md
            ├── report_*.html
            └── report_*.json
```

**⭐ = 新增或重写的文件**

---

### 1. `requirements.txt`
```
# Core LangChain & LangGraph
langchain==1.2.10
langgraph==1.0.8
langchain-openai>=0.1.8
langchain-community>=0.0.40

# Data & Financial Analysis
akshare>=1.18.0
pandas>=2.0.0
numpy>=1.24.0
pandas-ta>=0.4.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.0.0
requests>=2.31.0

# Logging
loguru>=0.7.0

# Development & Testing
pytest>=7.0.0
```

### 2. `.env.example`
```
# ============ LLM Provider Selection ============
# Options: claude, deepseek, kimi, qwen
LLM_PROVIDER=claude

# ============ Claude Configuration (Intermediary) ============
CLAUDE_API_KEY=your_api_key_here
CLAUDE_BASE_URL=https://your-intermediary-url/v1
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# ============ DeepSeek Configuration ============
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# ============ Kimi/Moonshot Configuration ============
KIMI_API_KEY=your_api_key_here
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-128k

# ============ Qwen/DashScope Configuration ============
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-max

# ============ Agent Parameters ============
PLANNER_TEMPERATURE=0.3
ANALYST_TEMPERATURE=0.5
DECIDER_TEMPERATURE=0.4
MAX_TOKENS=2000

# ============ Data Fetch Settings ============
DATA_FETCH_TIMEOUT=30

# ============ Logging ============
LOG_LEVEL=INFO
```

## 🔧 工作流程

```
START
  ↓
PLANNER (解析请求、提取股票代码)
  ↓
DATA_FETCHER (获取历史数据、基本面、新闻)
  ↓
  ├→ TECHNICAL_ANALYST (技术分析并行执行)
  │  ↓
  ├→ FUNDAMENTAL_ANALYST (基本面分析并行执行)
  │  ↓
REVIEWER (综合两份报告、检查矛盾)
  ↓
DECIDER (输出最终建议：BUY/HOLD/SELL)
  ↓
END (输出完整报告)
```

---

## 💡 核心特性

- **多 LLM 支持**：Claude、DeepSeek、Kimi、Qwen（都通过 OpenAI 兼容协议）
- **真实数据源**：AkShare 获取 A 股/港股/美股行情
- **并行分析**：技术面与基本面同时进行，提高效率
- **智能矛盾检测**：自动识别技术面与基本面的冲突信号
- **优雅降级**：数据缺失时继续进行分析，完整度得分跟踪
- **结构化输出**：JSON 格式报告，易于集成


---

## ❓ 常见问题

### Q: 如何切换 LLM？
A: 修改 `.env` 中的 `LLM_PROVIDER` 和对应的 API_KEY / BASE_URL，重新运行即可。

### Q: 支持哪些股票代码？
A:
- A 股：6 位代码如 600519.SH（沪深京三个交易所）
- 港股：如 0700.HK
- 美股：如 AAPL

### Q: 数据获取超时怎么办？
A: 修改 `.env` 中的 `DATA_FETCH_TIMEOUT`（秒数），或检查网络连接。

### Q: 如何调试某个 Agent？
A: 在 `main.py` 中修改 `debug=True`，会输出每个 Agent 的详细日志。

---

## 🔐 安全提示

- **不要提交 .env 文件**到 Git（添加到 .gitignore）
- **不要在代码中硬编码 API key**
- **定期轮换 API key**，特别是发现泄露时

---

## 📝 开发说明

### 添加新的 Agent
1. 在 `agents/` 目录创建新文件
2. 继承基础 Agent 模式（接收 State，返回 Dict）
3. 在 `graph.py` 中添加节点和边

### 添加新的 Tool
1. 在 `tools/` 目录相应文件中定义函数
2. 用 `@tool` 装饰器标注
3. 在 Agent 中通过 `tools` 参数传入

### 修改 State
编辑 `state.py` 中的 `FinancialAnalysisState` TypedDict，保证所有 Agent 兼容。

---

## 📞 支持

有问题？请检查：
1. `.env` 配置是否正确
2. API key 是否有效
3. 网络连接是否正常
4. Python 版本是否 ≥ 3.10

---

## 🗄️ Phase 3: 会话管理 (NEW)

Phase 3 引入了基于 SQLite 的对话历史存储和上下文管理功能。

### 数据库架构

系统自动创建 `agent.db` 数据库，包含以下表：

| 表名 | 功能 |
|------|------|
| `sessions` | 分析会话（含标题、创建时间） |
| `analyses` | 每次分析的结果（建议、置信度、完整状态） |
| `messages` | 会话内的对话消息历史 |
| `analysis_summaries` | 分析摘要（用于上下文压缩） |

### 会话使用示例

```bash
# 第一次分析（创建新会话）
python main.py
# → 选择 [1] 分析股票
# → 选择 [1] 创建新会话
# → 输入 600519.SH → 完成分析 → 自动保存

# 两周后再次分析（加载历史会话）
python main.py
# → 选择 [1] 分析股票
# → 选择 [2] 加载现有会话 → 选择之前的会话
# → 系统自动注入历史上下文到分析中！

# 查看会话列表
python main.py
# → 选择 [3] 管理会话
```

---

**最后修改**：2026-02-24
