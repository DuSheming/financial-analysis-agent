"""
Data Agent - 获取股票数据

负责：
1. 获取历史价格数据 (OHLCV)
2. 获取基本面数据 (PE、PB、ROE 等)
3. 获取最近新闻
"""

import json
import logging
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import llm_config
from state import FinancialAnalysisState
from tools.data_tools import fetch_stock_history, fetch_stock_info, fetch_stock_news

logger = logging.getLogger(__name__)


def data_agent(state: FinancialAnalysisState) -> Dict[str, Any]:
    """
    获取股票数据

    输入：symbol, date_range
    输出：historical_data, fundamentals, news, errors
    """
    try:
        symbol = state["symbol"]
        date_range = state.get("date_range") or {}
        start = date_range.get("start")
        end = date_range.get("end")

        logger.info(f"DataAgent: Fetching data for {symbol}")

        errors = []
        new_errors = state.get("errors", [])

        # 获取历史价格数据
        logger.info(f"DataAgent: Fetching history for {symbol}...")
        history_result = fetch_stock_history(symbol, start, end)
        if not history_result.get("success"):
            errors.append(f"Failed to fetch historical data: {history_result.get('error')}")
            historical_data = None
        else:
            historical_data = history_result.get("data")
            logger.info(f"DataAgent: Got {history_result.get('rows')} rows of data")

        # 获取基本面数据
        logger.info(f"DataAgent: Fetching fundamentals for {symbol}...")
        info_result = fetch_stock_info(symbol)
        fundamentals = info_result if info_result.get("success") else None
        if not info_result.get("success"):
            logger.warning(f"DataAgent: Fundamental data unavailable")

        # 获取新闻
        logger.info(f"DataAgent: Fetching news for {symbol}...")
        news_result = fetch_stock_news(symbol, limit=10)
        news = news_result.get("news") if news_result.get("success") else []
        logger.info(f"DataAgent: Got {len(news)} news items")

        # 数据质量评分
        quality_score = 1.0
        if not historical_data:
            quality_score -= 0.4
        if not fundamentals:
            quality_score -= 0.3
        if not news:
            quality_score -= 0.1

        return {
            "historical_data": historical_data,
            "fundamentals": fundamentals,
            "news": news,
            "data_quality": {
                "has_price_data": historical_data is not None,
                "has_fundamentals": fundamentals is not None,
                "has_news": len(news) > 0,
                "quality_score": max(0.0, quality_score),
            },
            "errors": new_errors + errors,
        }

    except Exception as e:
        logger.error(f"DataAgent error: {e}")
        return {
            "historical_data": None,
            "fundamentals": None,
            "news": None,
            "data_quality": {"quality_score": 0.0},
            "errors": state.get("errors", []) + [f"Data fetch error: {str(e)}"],
        }
