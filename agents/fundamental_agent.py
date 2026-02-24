"""
Fundamental Analyst Agent - 基本面分析

负责：
1. 分析估值 (PE、PB)
2. 分析增长 (收入增长率、利润增长率)
3. 分析新闻情绪
4. LLM 输出结构化基本面报告
"""

import json
import re
import logging
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import llm_config
from state import FinancialAnalysisState

logger = logging.getLogger(__name__)


def _parse_json_output(text: str) -> Dict[str, Any]:
    """健壮的 JSON 解析：处理 LLM 可能返回 Markdown 代码块的情况"""
    text = text.strip()

    # 1. 先尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 提取 ```json ... ``` 代码块
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 提取第一个 { ... } 对象
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Unable to parse JSON from output")


FUNDAMENTAL_ANALYSIS_PROMPT = """你是一位资深基本面分析师。请根据以下基本面数据对股票 {symbol} 进行综合基本面分析。

## 基本面数据

估值指标:
{fundamentals}

新闻信息:
{news}

## 分析要求

请综合所有数据，**只返回 JSON 对象，不要包含任何其他文字、解释或 Markdown 代码块**：

{{
    "valuation_assessment": "低估/合理/高估",
    "pe_ratio_analysis": "PE评价（如相对行业平均值）",
    "growth_potential": "强/中/弱",
    "competitive_advantages": ["竞争优势列表"],
    "risk_factors": ["基本面风险因素"],
    "news_sentiment": "积极/中立/消极",
    "industry_outlook": "行业前景评价",
    "management_quality": "管理层评价（如果能从数据推断）",
    "key_metrics": {{
        "roe": "净资产收益率评价",
        "debt_level": "负债水平评价"
    }},
    "investment_thesis": "投资逻辑简述",
    "summary": "100字以内的基本面综合评述"
}}
"""


def fundamental_analyst_agent(state: FinancialAnalysisState) -> Dict[str, Any]:
    """
    基本面分析

    输入：fundamentals, news
    输出：fundamental_report
    """
    try:
        symbol = state.get("symbol", "UNKNOWN")
        fundamentals = state.get("fundamentals")
        news = state.get("news", [])

        logger.info(f"FundamentalAnalyst: Analyzing {symbol}")

        # 简化的基本面数据
        fund_summary = {
            "available": fundamentals is not None,
            "pe_ratio": fundamentals.get("pe_ratio") if fundamentals else None,
            "pb_ratio": fundamentals.get("pb_ratio") if fundamentals else None,
            "roe": fundamentals.get("roe") if fundamentals else None,
            "industry": fundamentals.get("industry") if fundamentals else "Unknown",
        } if fundamentals else {"available": False, "note": "基本面数据不可用（可能是非A股）"}

        # 新闻摘要
        news_summary = [
            {"title": n.get("title", "")[:50], "date": n.get("date", "")}
            for n in news[:5]
        ] if news else []

        # LLM 综合分析
        logger.info(f"FundamentalAnalyst: Invoking LLM for {symbol}...")

        try:
            template = ChatPromptTemplate.from_template(FUNDAMENTAL_ANALYSIS_PROMPT)
            llm = llm_config.get_llm(temperature=llm_config.DEFAULT_TEMPERATURES["analyst"])
            chain = template | llm | StrOutputParser()

            raw_output = chain.invoke({
                "symbol": symbol,
                "fundamentals": json.dumps(fund_summary, ensure_ascii=False),
                "news": json.dumps(news_summary, ensure_ascii=False),
            })

            result = _parse_json_output(raw_output)
        except Exception as llm_e:
            logger.warning(f"LLM call failed, using fallback: {llm_e}")
            result = generate_fallback_report(symbol, fund_summary, news_summary)

        # 附加原始数据
        result["raw_data"] = {
            "fundamentals": fund_summary,
            "news_count": len(news),
        }

        logger.info(f"FundamentalAnalyst: Completed for {symbol}")
        return {"fundamental_report": result}

    except Exception as e:
        logger.error(f"FundamentalAnalyst error: {e}")
        return {
            "fundamental_report": {
                "valuation_assessment": "不确定",
                "growth_potential": "中",
                "summary": f"基本面分析过程中发生错误: {str(e)}",
                "error": str(e),
            }
        }


def generate_fallback_report(symbol: str, fundamentals: Dict, news: list) -> Dict[str, Any]:
    """
    LLM 失败时的降级方案
    """
    return {
        "valuation_assessment": "合理" if fundamentals.get("pe_ratio") and fundamentals["pe_ratio"] < 50 else "需评估",
        "growth_potential": "中",
        "news_sentiment": "中立",
        "summary": f"基本面数据有限，无法进行深度分析。PE 比率: {fundamentals.get('pe_ratio')}",
        "note": "LLM 不可用，使用简单规则分析",
    }
