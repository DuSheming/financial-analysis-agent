# 快速部署指南

## ✅ 已创建的文件清单

### 核心配置文件
- ✅ `config.py` - 多 LLM 工厂配置（支持 Claude、DeepSeek、Kimi、Qwen）
- ✅ `state.py` - LangGraph 状态定义
- ✅ `graph.py` - 工作流编排

### 工具模块 (tools/)
- ✅ `tools/__init__.py`
- ✅ `tools/data_tools.py` - AkShare 数据获取（历史价格、基本面、新闻）
- ✅ `tools/technical_tools.py` - 技术指标计算（RSI、MACD、MA、布林带）

### Agent 模块 (agents/)
- ✅ `agents/__init__.py`
- ✅ `agents/planner.py` - 请求解析 + 任务分解
- ✅ `agents/data_agent.py` - 数据获取协调
- ✅ `agents/technical_agent.py` - 技术面分析
- ✅ `agents/fundamental_agent.py` - 基本面分析
- ✅ `agents/reviewer.py` - 综合评审
- ✅ `agents/decider.py` - 最终决策

### 应用入口
- ✅ `main.py` - 应用主程序

### 文档
- ✅ `README.md` - 项目概述（包含 requirements.txt 和 .env.example 内容）
- ✅ `CLAUDE.md` - 代码文件索引
- ✅ `AGENTS.md` - 本文件（部署指南）

---

## 🚀 快速开始（5分钟）

### 第1步：安装依赖

从 `README.md` 复制 `requirements.txt` 的内容到 `Desktop/agent/requirements.txt`：

```bash
cd Desktop/agent
pip install -r requirements.txt
```

### 第2步：配置 LLM

从 `README.md` 复制 `.env.example` 的内容到 `Desktop/agent/.env`：

```bash
# 编辑 .env，填入你选择的 LLM 的 API key
# 比如使用 Claude（通过代理）：
LLM_PROVIDER=claude
CLAUDE_API_KEY=your_key_here
CLAUDE_BASE_URL=https://your-proxy/v1

# 或者使用 DeepSeek：
# LLM_PROVIDER=deepseek
# DEEPSEEK_API_KEY=your_key_here

# 或者使用 Kimi：
# LLM_PROVIDER=kimi
# KIMI_API_KEY=your_key_here

# 或者使用 Qwen：
# LLM_PROVIDER=qwen
# QWEN_API_KEY=your_key_here
```

### 第3步：运行分析

```bash
# 分析贵州茅台（默认）
python main.py

# 或指定股票
python main.py "分析 000858.SZ，给出 6 个月投资建议"
python main.py "分析 0700.HK（腾讯），判断是否值得长期持有"
python main.py "分析 AAPL（苹果），给出交易信号"
```

---

## 📋 工作流详解

```
用户请求: "分析 600519.SH，给出长期投资建议"
    ↓
┌─────────────────────────────────────────────────────┐
│ 1️⃣  PLANNER: 解析请求                                   │
│    - 提取股票代码: 600519.SH                             │
│    - 确定分析周期: 2024-02-18 ~ 2025-02-18             │
│    - 分解任务列表                                        │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ 2️⃣  DATA FETCHER: 获取数据                              │
│    - fetch_stock_history() → 365 天 OHLCV 数据          │
│    - fetch_stock_info() → PE/PB/ROE 等                 │
│    - fetch_stock_news() → 最近 10 条新闻                │
└─────────────────────────────────────────────────────┘
    ↓
    ├─────────────────────────────────────────────────┐  ┌───────────────────────────────────────────┐
    │ 3️⃣  TECHNICAL ANALYST（并行）                      │  │ 4️⃣  FUNDAMENTAL ANALYST（并行）           │
    │    - calculate_rsi(14)                            │  │    - 估值分析（PE/PB）                     │
    │    - calculate_macd(12,26,9)                      │  │    - 增长分析（收入/利润增速）             │
    │    - calculate_moving_averages([20,60,120,250])   │  │    - 新闻情绪分析                          │
    │    - calculate_bollinger_bands()                  │  │    - LLM 综合基本面                        │
    │    - LLM 综合解读所有指标 → technical_report      │  │       → fundamental_report                │
    └─────────────────────────────────────────────────┘  └───────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ 5️⃣  REVIEWER: 综合评审                                  │
│    - 检查技术面 vs 基本面是否矛盾                        │
│    - 识别看多/看空因素                                   │
│    - LLM 生成统一评审报告                                │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ 6️⃣  DECIDER: 最终决策                                   │
│    - BUY / HOLD / SELL                               │
│    - 入场价、止损价、目标价                              │
│    - 持有周期、风险、机会                                │
│    - 信心度量化                                         │
└─────────────────────────────────────────────────────┘
    ↓
输出完整分析报告
```

---

## 🔧 多 LLM 快速切换

所有 LLM 都通过 OpenAI 兼容 API 接入，切换只需修改 `.env`：

### Claude（通过代理）
```bash
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-...
CLAUDE_BASE_URL=https://api.openai-proxy.com/v1  # 你的代理 URL
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

### DeepSeek（直连）
```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

### Kimi/Moonshot
```bash
LLM_PROVIDER=kimi
KIMI_API_KEY=...
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-128k
```

### Qwen/DashScope
```bash
LLM_PROVIDER=qwen
QWEN_API_KEY=...
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-max
```

---

## 📊 支持的股票代码格式

| 市场 | 格式 | 示例 |
|------|------|------|
| A 股（沪） | XXXXXX.SH | 600519.SH（贵州茅台） |
| A 股（深） | XXXXXX.SZ | 000858.SZ（五粮液） |
| 港股 | XXXX.HK | 0700.HK（腾讯） |
| 美股 | XXXX | AAPL（苹果） |

---

## 🐛 常见问题排查

### 问题 1: `ModuleNotFoundError: No module named 'akshare'`
**解决**：
```bash
pip install --upgrade akshare
```

### 问题 2: `ValueError: CLAUDE_API_KEY and CLAUDE_BASE_URL required`
**解决**：检查 `.env` 文件是否存在且填写了正确的 API key 和 base_url

### 问题 3: AkShare 数据获取失败
**解决**：
- 检查网络连接
- 修改 `DATA_FETCH_TIMEOUT` 为更大的值
- 或者暂时切换到有代理的网络

### 问题 4: LLM 调用超时
**解决**：
- 检查 API key 是否有效
- 检查网络连接和代理配置
- 尝试调整 `MAX_TOKENS` 参数

### 问题 5: 返回结果为空或 "N/A"
**解决**：
- 数据质量可能受限（某些 LLM 数据不完整）
- 尝试切换到另一个 LLM
- 使用不同的股票代码测试

---

## 📈 输出示例

```
================================================================================
                    分析完成 - 最终报告
================================================================================

📊 股票代码: 600519.SH
📅 分析时间: 2025-02-18 14:32:15

📈 数据质量:
  - 价格数据: ✓
  - 基本面数据: ✓
  - 新闻数据: ✓
  - 总体评分: 100.0%

📉 技术分析:
  - 趋势: 上升
  - 强度: 强
  - 短期信号: 持有
  - 关键观察:
    • RSI 接近 70，处于超买区域
    • MACD 呈正向背离
    • 价格在 MA120 上方

💰 基本面分析:
  - 估值评估: 偏高
  - 增长潜力: 强
  - 新闻情绪: 积极

🔍 综合评审:
  - 共识水平: 部分共识
  - 整体情绪: 看多但谨慎
  - 信心水平: 72%
  - 矛盾点数: 1

✅ 最终投资建议:
  - 建议: 持有
  - 信心度: 72%
  - 目标价: 200.0
  - 止损价: 165.0
  - 持有周期: 6-12 个月
  - 建议仓位: 正常

📝 决策理由:
  长期基本面强劲，支持继续上升，但短期技术超买需要谨慎。
  建议在调整到 160-170 区间时加仓，目标价位 200+。

⚡ 主要风险:
  • 估值压力（PE 40+ 处于高位）
  • 宏观经济波动影响消费
  • 政策风险（食品安全等）

🎯 主要机会:
  • 长期消费升级趋势
  • 龙头品牌护城河深
  • 国际化扩展潜力

================================================================================
更多详细分析请查看完整报告
================================================================================
```

---

## 🔐 安全提示

1. **不要提交 .env 到 Git**：
   ```bash
   echo ".env" >> .gitignore
   ```

2. **定期轮换 API Key**

3. **不要在代码中硬编码敏感信息**

---

## 💡 使用建议

1. **首次运行**：用 `600519.SH`（茅台）或 `000858.SZ`（五粮液）测试，这些股票数据完整

2. **调整分析深度**：
   - 如需快速分析：降低 `MAX_TOKENS` 到 1000
   - 如需深度分析：增加到 3000

3. **多 LLM 对比**：
   - DeepSeek：便宜（¥0.14 per 1M tokens）
   - Claude：平衡（¥0.75 per 1M tokens）
   - Qwen：国产（¥0.008 per 1M tokens）

4. **生产环境**：
   - 添加错误重试机制
   - 实现数据缓存（避免重复调用 AkShare）
   - 使用专业级的日志系统

---

## 📞 故障排查 Checklist

- [ ] Python 版本 ≥ 3.10
- [ ] `pip install -r requirements.txt` 成功
- [ ] `.env` 文件存在且配置正确
- [ ] 至少一个 LLM 的 API Key 有效
- [ ] 网络连接正常
- [ ] 首次运行用默认股票代码测试

---

**祝你使用愉快！有问题请查看 README.md 或排查常见问题。**
