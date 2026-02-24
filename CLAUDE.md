# 代码文件创建指南

本文档包含所有需要创建的 Python 代码文件。每个部分标明了真实的文件路径，你可以直接复制代码创建对应文件。

---

## 文件 1: `config.py` - 多 LLM 工厂配置

**路径**: `Desktop/agent/config.py`

```python
import os
from typing import Optional
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class LLMConfig:
    """多 LLM 提供商配置工厂"""

    # 支持的 LLM 提供商
    PROVIDERS = ["claude", "deepseek", "kimi", "qwen"]

    # 默认温度设置（可通过环境变量覆盖）
    DEFAULT_TEMPERATURES = {
        "planner": float(os.getenv("PLANNER_TEMPERATURE", "0.3")),
        "analyst": float(os.getenv("ANALYST_TEMPERATURE", "0.5")),
        "decider": float(os.getenv("DECIDER_TEMPERATURE", "0.4")),
    }

    # 默认参数
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
    TIMEOUT = int(os.getenv("DATA_FETCH_TIMEOUT", "30"))

    @staticmethod
    def get_llm(temperature: float = 0.5) -> ChatOpenAI:
        """
        获取配置的 LLM 实例

        Args:
            temperature: LLM 温度参数 (0.0-1.0)

        Returns:
            ChatOpenAI 实例，使用 OpenAI 兼容 API
        """
        provider = os.getenv("LLM_PROVIDER", "claude").lower()

        if provider not in LLMConfig.PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}. Use one of {LLMConfig.PROVIDERS}")

        if provider == "claude":
            api_key = os.getenv("CLAUDE_API_KEY")
            base_url = os.getenv("CLAUDE_BASE_URL")
            model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

            if not api_key or not base_url:
                raise ValueError("CLAUDE_API_KEY and CLAUDE_BASE_URL must be set in .env")

            return ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=LLMConfig.MAX_TOKENS,
            )

        elif provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
            model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY must be set in .env")

            return ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=LLMConfig.MAX_TOKENS,
            )

        elif provider == "kimi":
            api_key = os.getenv("KIMI_API_KEY")
            base_url = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
            model = os.getenv("KIMI_MODEL", "moonshot-v1-128k")

            if not api_key:
                raise ValueError("KIMI_API_KEY must be set in .env")

            return ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=LLMConfig.MAX_TOKENS,
            )

        elif provider == "qwen":
            api_key = os.getenv("QWEN_API_KEY")
            base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            model = os.getenv("QWEN_MODEL", "qwen-max")

            if not api_key:
                raise ValueError("QWEN_API_KEY must be set in .env")

            return ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=LLMConfig.MAX_TOKENS,
            )

# 全局配置单例
llm_config = LLMConfig()
```

---

## 文件 2: `state.py` - 增强的状态定义

**路径**: `Desktop/agent/state.py`

```python
from typing import TypedDict, List, Optional, Dict, Any

class FinancialAnalysisState(TypedDict):
    """
    金融分析 LangGraph 工作流状态定义

    所有字段都应是不可变的，Agent 返回新值而非修改现有值。
    """
    # 基础信息
    initial_request: str  # 用户初始请求
    planned_tasks: List[str]  # Planner Agent 分解的任务列表
    symbol: str  # 股票代码 (如 "600519.SH")
    date_range: Optional[Dict[str, str]]  # {"start": "2024-01-01", "end": "2025-02-18"}

    # 数据层
    historical_data: Optional[str]  # JSON 格式的历史价格数据
    fundamentals: Optional[Dict[str, Any]]  # 基本面数据 {pe, pb, revenue_growth, ...}
    news: Optional[List[Dict[str, str]]]  # 新闻列表 [{"title": "...", "date": "...", "sentiment": "..."}]

    # 分析报告
    technical_report: Optional[Dict[str, Any]]  # 技术分析报告
    fundamental_report: Optional[Dict[str, Any]]  # 基本面分析报告
    reviewer_summary: Optional[Dict[str, Any]]  # 综合评审报告
    final_recommendation: Optional[Dict[str, Any]]  # 最终建议

    # 质量和错误追踪
    errors: List[str]  # 错误信息列表，支持优雅降级
    data_quality: Optional[Dict[str, Any]]  # 数据质量评分
```

---

## 文件 3: `tools/data_tools.py` - AkShare 数据获取

**路径**: `Desktop/agent/tools/data_tools.py`

```python
"""
AkShare 数据获取工具

提供股票历史数据、基本面数据、新闻等获取功能。
"""

import akshare as ak
import pandas as pd
import json
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def validate_symbol(symbol: str) -> bool:
    """验证股票代码格式"""
    if not symbol or not isinstance(symbol, str):
        return False
    # 支持格式: 600519.SH (A股), 0700.HK (港股), AAPL (美股)
    valid_formats = [
        lambda s: len(s) == 8 and s[6:] in [".SH", ".SZ"],  # A股
        lambda s: len(s) == 8 and s[4:] == ".HK",  # 港股
        lambda s: 1 <= len(s) <= 5 and s.isupper(),  # 美股
    ]
    return any(fmt(symbol) for fmt in valid_formats)

def fetch_stock_history(
    symbol: str,
    start_date: str = None,
    end_date: str = None,
    period: str = "daily"
) -> Dict[str, Any]:
    """
    获取股票历史价格数据

    Args:
        symbol: 股票代码 (如 "600519.SH")
        start_date: 开始日期 "YYYY-MM-DD"，默认过去一年
        end_date: 结束日期 "YYYY-MM-DD"，默认今天
        period: 周期 "daily" / "weekly" / "monthly"

    Returns:
        {
            "success": bool,
            "data": JSON 字符串 (OHLCV 数据),
            "rows": int,
            "error": str (如果失败)
        }
    """
    try:
        if not validate_symbol(symbol):
            return {"success": False, "error": f"Invalid symbol format: {symbol}"}

        # 默认日期范围：过去一年
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        # 根据股票类型调用不同的 AkShare 接口
        if symbol.endswith(".SH") or symbol.endswith(".SZ"):
            # A股
            symbol_code = symbol[:6]  # 提取代码部分
            df = ak.stock_zh_a_hist(
                symbol=symbol_code,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq"  # 前复权
            )
        elif symbol.endswith(".HK"):
            # 港股
            symbol_code = symbol[:4]
            df = ak.hk_hq_daily(symbol=symbol_code)
            # 按日期范围筛选
            df['trade_date'] = pd.to_datetime(df.get('trade_date', df.get('date', pd.Series())))
            df = df[(df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)]
        else:
            # 美股
            df = ak.us_symbol_chart(symbol=symbol)
            df['date'] = pd.to_datetime(df.get('date', pd.Series()))
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

        if df.empty:
            return {"success": False, "error": f"No data found for {symbol}"}

        # 转换为 JSON
        data_json = df.to_json(orient="records", date_format="iso")

        return {
            "success": True,
            "symbol": symbol,
            "data": data_json,
            "rows": len(df),
            "start_date": start_date,
            "end_date": end_date,
            "last_close": float(df.iloc[-1].get('close', df.iloc[-1].get('最新价', 0)))
        }

    except Exception as e:
        logger.error(f"Error fetching history for {symbol}: {str(e)}")
        return {
            "success": False,
            "symbol": symbol,
            "error": f"Failed to fetch data: {str(e)}"
        }

def fetch_stock_info(symbol: str) -> Dict[str, Any]:
    """
    获取股票基本信息（PE、PB、市值等）

    Args:
        symbol: 股票代码

    Returns:
        {
            "success": bool,
            "pe_ratio": float,
            "pb_ratio": float,
            "market_cap": str,
            "revenue_growth": float,
            "profit_growth": float,
            "error": str
        }
    """
    try:
        if not validate_symbol(symbol):
            return {"success": False, "error": f"Invalid symbol format: {symbol}"}

        if symbol.endswith((".SH", ".SZ")):
            # A股基本面数据
            symbol_code = symbol[:6]
            try:
                # 尝试获取个股信息
                df = ak.stock_individual_info_em(symbol=symbol_code)
                info = df.set_index(0)[1].to_dict() if not df.empty else {}
            except:
                info = {}

            # 提取关键指标
            return {
                "success": True,
                "symbol": symbol,
                "pe_ratio": float(info.get("滚动市盈率", 0)) if info.get("滚动市盈率") else None,
                "pb_ratio": float(info.get("市净率", 0)) if info.get("市净率") else None,
                "roe": float(info.get("ROE", 0)) if info.get("ROE") else None,
                "market_cap": info.get("总市值", "N/A"),
            }
        else:
            # 港股/美股：简化处理
            return {
                "success": True,
                "symbol": symbol,
                "pe_ratio": None,
                "pb_ratio": None,
                "note": "Limited data for non-A-share stocks"
            }

    except Exception as e:
        logger.error(f"Error fetching info for {symbol}: {str(e)}")
        return {
            "success": False,
            "symbol": symbol,
            "error": f"Failed to fetch info: {str(e)}"
        }

def fetch_stock_news(symbol: str, limit: int = 10) -> Dict[str, Any]:
    """
    获取股票最近新闻

    Args:
        symbol: 股票代码
        limit: 新闻数量限制

    Returns:
        {
            "success": bool,
            "news": [{"title": str, "date": str, "source": str}, ...],
            "error": str
        }
    """
    try:
        if not validate_symbol(symbol):
            return {"success": False, "error": f"Invalid symbol format: {symbol}"}

        symbol_code = symbol[:6] if symbol.endswith((".SH", ".SZ")) else symbol

        # 获取财经新闻
        try:
            df = ak.stock_news_em(symbol=symbol_code)
            if df.empty:
                return {"success": True, "news": [], "symbol": symbol}

            news_list = []
            for idx, row in df.head(limit).iterrows():
                news_list.append({
                    "title": str(row.get("新闻标题", row.get("title", ""))),
                    "date": str(row.get("发布日期", row.get("date", ""))),
                    "source": str(row.get("来源", row.get("source", ""))),
                    "sentiment": "neutral"  # 简化处理，不做情感分析
                })

            return {
                "success": True,
                "symbol": symbol,
                "news": news_list
            }
        except:
            return {"success": True, "news": [], "symbol": symbol}

    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {str(e)}")
        return {
            "success": False,
            "symbol": symbol,
            "error": f"Failed to fetch news: {str(e)}"
        }
```

---

## 文件 4: `tools/technical_tools.py` - 技术指标计算

**路径**: `Desktop/agent/tools/technical_tools.py`

```python
"""
技术指标计算工具

使用 pandas-ta 库计算 RSI、MACD、移动平均线等指标。
"""

import pandas as pd
import json
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

def parse_data_from_json(data_json: str) -> pd.DataFrame:
    """从 JSON 字符串解析为 DataFrame"""
    try:
        data = json.loads(data_json)
        df = pd.DataFrame(data)

        # 标准化列名
        df.columns = df.columns.str.lower()

        # 确保有必要的列
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                # 尝试找替代列名
                for alias in [[f'{col}e', f'{col}_price'], []]:
                    for a in alias:
                        if a in df.columns:
                            df[col] = df[a]
                            break

        # 确保数值类型
        for col in required_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df.dropna(subset=required_cols)
    except Exception as e:
        logger.error(f"Error parsing data: {str(e)}")
        raise

def calculate_rsi(data_json: str, period: int = 14) -> Dict[str, Any]:
    """
    计算相对强度指数 (RSI)

    RSI > 70: 超买
    RSI < 30: 超卖
    """
    try:
        df = parse_data_from_json(data_json)

        # 手动计算 RSI（不依赖 pandas-ta）
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        latest_rsi = float(rsi.iloc[-1])

        # 判断超买/超卖
        if latest_rsi > 70:
            signal = "overbought"
        elif latest_rsi < 30:
            signal = "oversold"
        else:
            signal = "neutral"

        return {
            "success": True,
            "indicator": "RSI",
            "period": period,
            "value": round(latest_rsi, 2),
            "signal": signal,
            "interpretation": f"RSI {latest_rsi:.1f} - {signal.upper()}"
        }

    except Exception as e:
        logger.error(f"Error calculating RSI: {str(e)}")
        return {"success": False, "error": str(e)}

def calculate_macd(data_json: str, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Any]:
    """
    计算 MACD (Moving Average Convergence Divergence)

    返回: MACD线, Signal线, Histogram
    """
    try:
        df = parse_data_from_json(data_json)

        # 计算 EMA
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

        # MACD线
        macd_line = ema_fast - ema_slow

        # Signal线
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()

        # 柱状图
        histogram = macd_line - signal_line

        latest_macd = float(macd_line.iloc[-1])
        latest_signal = float(signal_line.iloc[-1])
        latest_histogram = float(histogram.iloc[-1])

        # 判断信号
        if latest_histogram > 0 and histogram.iloc[-2] <= 0:
            macd_signal = "bullish_cross"
        elif latest_histogram < 0 and histogram.iloc[-2] >= 0:
            macd_signal = "bearish_cross"
        elif latest_histogram > 0:
            macd_signal = "bullish"
        else:
            macd_signal = "bearish"

        return {
            "success": True,
            "indicator": "MACD",
            "macd": round(latest_macd, 4),
            "signal": round(latest_signal, 4),
            "histogram": round(latest_histogram, 4),
            "interpretation": macd_signal
        }

    except Exception as e:
        logger.error(f"Error calculating MACD: {str(e)}")
        return {"success": False, "error": str(e)}

def calculate_moving_averages(data_json: str, periods: List[int] = None) -> Dict[str, Any]:
    """
    计算多条移动平均线 (MA)

    常用周期: [20, 50, 120, 250] (日线)
    """
    if periods is None:
        periods = [20, 60, 120, 250]

    try:
        df = parse_data_from_json(data_json)

        mas = {}
        for period in periods:
            if period <= len(df):
                ma = df['close'].rolling(window=period).mean()
                mas[f"MA{period}"] = round(float(ma.iloc[-1]), 2)

        # 判断趋势
        if len(mas) >= 2:
            ma_values = list(mas.values())
            if all(ma_values[i] >= ma_values[i+1] for i in range(len(ma_values)-1)):
                trend = "downtrend"
            elif all(ma_values[i] <= ma_values[i+1] for i in range(len(ma_values)-1)):
                trend = "uptrend"
            else:
                trend = "consolidating"
        else:
            trend = "unknown"

        return {
            "success": True,
            "indicator": "Moving Averages",
            "values": mas,
            "trend": trend
        }

    except Exception as e:
        logger.error(f"Error calculating MA: {str(e)}")
        return {"success": False, "error": str(e)}

def calculate_bollinger_bands(data_json: str, period: int = 20, std_dev: float = 2) -> Dict[str, Any]:
    """
    计算布林带 (Bollinger Bands)
    """
    try:
        df = parse_data_from_json(data_json)

        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        latest_close = float(df['close'].iloc[-1])
        latest_upper = float(upper_band.iloc[-1])
        latest_middle = float(sma.iloc[-1])
        latest_lower = float(lower_band.iloc[-1])

        # 判断价格位置
        if latest_close >= latest_upper:
            position = "at_upper_band"
        elif latest_close <= latest_lower:
            position = "at_lower_band"
        else:
            position = "within_bands"

        return {
            "success": True,
            "indicator": "Bollinger Bands",
            "upper": round(latest_upper, 2),
            "middle": round(latest_middle, 2),
            "lower": round(latest_lower, 2),
            "current_price": round(latest_close, 2),
            "position": position
        }

    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands: {str(e)}")
        return {"success": False, "error": str(e)}
```

---

## 文件 5: `tools/__init__.py`

**路径**: `Desktop/agent/tools/__init__.py`

```python
"""Tools 模块 - 所有数据和分析工具"""

from .data_tools import (
    fetch_stock_history,
    fetch_stock_info,
    fetch_stock_news,
    validate_symbol,
)

from .technical_tools import (
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_bollinger_bands,
)

__all__ = [
    "fetch_stock_history",
    "fetch_stock_info",
    "fetch_stock_news",
    "validate_symbol",
    "calculate_rsi",
    "calculate_macd",
    "calculate_moving_averages",
    "calculate_bollinger_bands",
]
```

---

（继续下一部分...）
