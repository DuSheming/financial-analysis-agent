"""
Technical Analyst Agent - 技术面分析

负责：
1. 计算 RSI、MACD、移动平均线、布林带
2. LLM 综合解读所有技术指标
3. 输出结构化技术分析报告
"""

import json
import re
import logging
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import llm_config
from state import FinancialAnalysisState
from tools.technical_tools import (
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_bollinger_bands,
)

logger = logging.getLogger(__name__)


TECHNICAL_ANALYSIS_PROMPT = """你是一位资深技术分析师。请根据以下技术指标数据对股票 {symbol} 进行综合技术分析。

## 技术指标数据

RSI 指标:
{rsi}

MACD 指标:
{macd}

移动平均线:
{ma}

布林带:
{bb}

## 分析要求

请综合所有指标，**只返回 JSON 对象，不要包含任何其他文字、解释或 Markdown 代码块**：

{{
    "trend": "上升/下降/震荡",
    "strength": "强/中/弱",
    "short_term_signal": "买入/卖出/持有",
    "overbought_signals": ["超买信号列表"],
    "oversold_signals": ["超卖信号列表"],
    "support_level": "支撑位估计（如果可以从均线推断）",
    "resistance_level": "阻力位估计",
    "key_observations": ["关键观察点1", "关键观察点2"],
    "risk_factors": ["技术面风险因素"],
    "summary": "100字以内的技术面综合评述"
}}
"""


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

    raise ValueError(f"无法从 LLM 输出中解析 JSON:\n{text[:500]}")


def technical_analyst_agent(state: FinancialAnalysisState) -> Dict[str, Any]:
    """
    技术面分析

    输入：historical_data
    输出：technical_report
    """
    try:
        symbol = state.get("symbol", "UNKNOWN")
        historical_data = state.get("historical_data")

        if not historical_data:
            logger.warning(f"TechnicalAnalyst: No historical data for {symbol}")
            return {
                "technical_report": {
                    "trend": "N/A",
                    "short_term_signal": "持有",
                    "key_observations": ["无法获取历史数据，技术分析不可用"],
                    "summary": "由于缺少历史价格数据，技术分析无法完成。",
                    "error": "No historical data available",
                }
            }

        logger.info(f"TechnicalAnalyst: Calculating indicators for {symbol}...")

        # 计算技术指标
        rsi = calculate_rsi(historical_data)
        macd = calculate_macd(historical_data)
        ma = calculate_moving_averages(historical_data)
        bb = calculate_bollinger_bands(historical_data)

        # 记录错误的指标
        indicator_errors = []
        for name, result in [("RSI", rsi), ("MACD", macd), ("MA", ma), ("BB", bb)]:
            if not result.get("success"):
                indicator_errors.append(f"{name}: {result.get('error')}")

        logger.info(f"TechnicalAnalyst: Indicators calculated, invoking LLM...")

        # LLM 综合解读 - 使用 StrOutputParser 后手动解析 JSON
        template = ChatPromptTemplate.from_template(TECHNICAL_ANALYSIS_PROMPT)
        llm = llm_config.get_llm(temperature=llm_config.DEFAULT_TEMPERATURES["analyst"])
        chain = template | llm | StrOutputParser()

        raw_output = chain.invoke({
            "symbol": symbol,
            "rsi": json.dumps(rsi, ensure_ascii=False),
            "macd": json.dumps(macd, ensure_ascii=False),
            "ma": json.dumps(ma, ensure_ascii=False),
            "bb": json.dumps(bb, ensure_ascii=False),
        })

        result = _parse_json_output(raw_output)

        # 附加原始指标数据
        result["raw_indicators"] = {
            "rsi": rsi,
            "macd": macd,
            "moving_averages": ma,
            "bollinger_bands": bb,
        }

        if indicator_errors:
            result["indicator_errors"] = indicator_errors

        logger.info(f"TechnicalAnalyst: Completed for {symbol}")
        return {"technical_report": result}

    except Exception as e:
        logger.error(f"TechnicalAnalyst error: {e}")
        return {
            "technical_report": {
                "trend": "N/A",
                "short_term_signal": "持有",
                "summary": f"技术分析过程中发生错误: {str(e)}",
                "error": str(e),
            }
        }
