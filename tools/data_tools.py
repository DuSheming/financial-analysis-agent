"""
AkShare 数据获取工具

提供股票历史数据、基本面数据、新闻等获取功能。
支持 A 股 (600519.SH)、港股 (0700.HK)、美股 (AAPL)。
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def validate_symbol(symbol: str) -> bool:
    """验证股票代码格式"""
    if not symbol or not isinstance(symbol, str):
        return False
    s = symbol.strip().upper()
    # A 股: 600519.SH / 000858.SZ / 000001.BJ
    if len(s) == 9 and s[:6].isdigit() and s[6] == "." and s[7:] in ("SH", "SZ", "BJ"):
        return True
    # 港股: 0700.HK (4 位数字 + .HK)
    if len(s) == 7 and s[:4].isdigit() and s[4:] == ".HK":
        return True
    # 美股: 1-5 位字母
    if 1 <= len(s) <= 5 and s.isalpha():
        return True
    return False


def fetch_stock_history(
    symbol: str,
    start_date: str = None,
    end_date: str = None,
) -> Dict[str, Any]:
    """
    获取股票历史价格数据 (OHLCV)

    Args:
        symbol: 股票代码 (如 "600519.SH")
        start_date: 开始日期 "YYYY-MM-DD"，默认过去一年
        end_date: 结束日期 "YYYY-MM-DD"，默认今天

    Returns:
        {"success": bool, "data": JSON, "rows": int, "last_close": float, "error": str}
    """
    try:
        import akshare as ak
        import pandas as pd

        if not validate_symbol(symbol):
            return {"success": False, "error": f"Invalid symbol format: {symbol}"}

        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        s = symbol.strip().upper()

        if s.endswith((".SH", ".SZ", ".BJ")):
            code = s[:6]
            df = ak.stock_zh_a_hist(
                symbol=code,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq",
            )
            # 统一列名（AkShare 返回中文列名）
            col_map = {
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
            }
            df = df.rename(columns=col_map)

        elif s.endswith(".HK"):
            code = s[:4]
            df = ak.hk_hq_daily(symbol=code)
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]

        else:
            # 美股简化处理
            df = ak.stock_us_spot_em()
            df = df[df["代码"] == s].head(1) if not df.empty else pd.DataFrame()
            if df.empty:
                return {"success": False, "error": f"US stock {symbol} not found"}

        if df.empty:
            return {"success": False, "error": f"No data returned for {symbol}"}

        # 只保留需要的列
        keep = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[keep].dropna()

        last_close = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0

        return {
            "success": True,
            "symbol": symbol,
            "data": df.to_json(orient="records", date_format="iso"),
            "rows": len(df),
            "start_date": start_date,
            "end_date": end_date,
            "last_close": round(last_close, 2),
        }

    except Exception as e:
        logger.error(f"fetch_stock_history error [{symbol}]: {e}")
        return {"success": False, "symbol": symbol, "error": str(e)}


def fetch_stock_info(symbol: str) -> Dict[str, Any]:
    """
    获取股票基本面信息（PE、PB、ROE、市值等）

    Args:
        symbol: 股票代码

    Returns:
        {"success": bool, "pe_ratio": float, "pb_ratio": float, "roe": float, ...}
    """
    try:
        import akshare as ak

        if not validate_symbol(symbol):
            return {"success": False, "error": f"Invalid symbol: {symbol}"}

        s = symbol.strip().upper()

        if not s.endswith((".SH", ".SZ", ".BJ")):
            return {
                "success": True,
                "symbol": symbol,
                "note": "Fundamental data only available for A-shares",
            }

        code = s[:6]
        df = ak.stock_individual_info_em(symbol=code)

        if df.empty:
            return {"success": False, "error": "No fundamental data available"}

        # AkShare 返回两列：指标名 (item=0) 和 值 (item=1)
        df.columns = ["key", "value"]
        info = dict(zip(df["key"].tolist(), df["value"].tolist()))

        def safe_float(val):
            try:
                return float(str(val).replace(",", "").replace("%", ""))
            except:
                return None

        return {
            "success": True,
            "symbol": symbol,
            "pe_ratio": safe_float(info.get("市盈率(动态)")),
            "pb_ratio": safe_float(info.get("市净率")),
            "roe": safe_float(info.get("净资产收益率")),
            "market_cap": info.get("总市值", "N/A"),
            "industry": info.get("所处行业", "N/A"),
            "raw": info,
        }

    except Exception as e:
        logger.error(f"fetch_stock_info error [{symbol}]: {e}")
        return {"success": False, "symbol": symbol, "error": str(e)}


def fetch_stock_news(symbol: str, limit: int = 10) -> Dict[str, Any]:
    """
    获取股票最近新闻

    Args:
        symbol: 股票代码
        limit: 返回新闻条数

    Returns:
        {"success": bool, "news": [{"title": str, "date": str}, ...]}
    """
    try:
        import akshare as ak

        if not validate_symbol(symbol):
            return {"success": False, "error": f"Invalid symbol: {symbol}"}

        s = symbol.strip().upper()
        code = s[:6] if s.endswith((".SH", ".SZ", ".BJ")) else s

        news_list: List[Dict[str, str]] = []
        try:
            df = ak.stock_news_em(symbol=code)
            if not df.empty:
                for _, row in df.head(limit).iterrows():
                    news_list.append({
                        "title": str(row.get("新闻标题", row.get("title", ""))),
                        "date": str(row.get("发布时间", row.get("date", ""))),
                        "source": str(row.get("文章来源", row.get("source", ""))),
                    })
        except Exception as inner_e:
            logger.warning(f"News fetch warning [{symbol}]: {inner_e}")

        return {"success": True, "symbol": symbol, "news": news_list}

    except Exception as e:
        logger.error(f"fetch_stock_news error [{symbol}]: {e}")
        return {"success": False, "symbol": symbol, "error": str(e)}
