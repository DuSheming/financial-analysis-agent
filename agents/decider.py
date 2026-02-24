"""
Decider Agent - 最终决策

负责：
1. 综合评审报告
2. 生成投资建议 (BUY/HOLD/SELL)
3. 给出具体的入场点、止损、目标价
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


DECIDER_PROMPT = """你是一位资深的投资决策顾问。请根据以下综合评审报告为股票 {symbol} 生成最终的投资建议。

股票代码: {symbol}
当前价格（参考）: {current_price}

## 综合评审报告
{reviewer_summary}

## 决策要求

请以 **JSON 格式返回以下结构，不要包含任何其他文字或 Markdown 代码块**：

{{
    "recommendation": "买入/持有/卖出",
    "confidence": 0.75,
    "entry_price": "建议入场价（如果建议买入）",
    "target_price": "目标价格",
    "stop_loss": "止损价格",
    "holding_period": "建议持有周期（如 3-6个月, 12个月）",
    "position_size": "建议仓位（轻仓/正常/重仓）",
    "key_monitoring_points": [
        "监控指标1",
        "监控指标2"
    ],
    "exit_signals": [
        "触发卖出信号的条件1",
        "触发卖出信号的条件2"
    ],
    "risks": [
        "主要风险1",
        "主要风险2"
    ],
    "opportunities": [
        "主要机会1",
        "主要机会2"
    ],
    "reasoning": "决策推理过程（200字以内）"
}}

## 决策逻辑参考

- 如果综合评审中看多因素明显多于看空，且信心高 → 买入
- 如果矛盾较多或信心不足 → 持有
- 如果看空因素明显多于看多 → 卖出
- 建议给出具体的价格目标和风险点位
"""


def decider_agent(state: FinancialAnalysisState) -> Dict[str, Any]:
    """
    最终投资决策

    输入：reviewer_summary, symbol, fundamentals
    输出：final_recommendation
    """
    try:
        symbol = state.get("symbol", "UNKNOWN")
        review = state.get("reviewer_summary") or {}
        fundamentals = state.get("fundamentals") or {}

        logger.info(f"Decider: Making final decision for {symbol}")

        # 提取当前价格（从基本面或默认）
        current_price = fundamentals.get("last_close", 0) or "不可用"

        # LLM 决策
        logger.info(f"Decider: Invoking LLM for {symbol}...")

        try:
            template = ChatPromptTemplate.from_template(DECIDER_PROMPT)
            llm = llm_config.get_llm(temperature=llm_config.DEFAULT_TEMPERATURES["decider"])
            chain = template | llm | StrOutputParser()

            raw_output = chain.invoke({
                "symbol": symbol,
                "current_price": current_price,
                "reviewer_summary": json.dumps(review, ensure_ascii=False),
            })

            result = _parse_json_output(raw_output)
        except Exception as llm_e:
            logger.warning(f"LLM call failed, using fallback decision: {llm_e}")
            result = generate_fallback_decision(symbol, review)

        logger.info(f"Decider: Final recommendation is {result.get('recommendation')} for {symbol}")
        return {"final_recommendation": result}

    except Exception as e:
        logger.error(f"Decider error: {e}")
        return {
            "final_recommendation": {
                "recommendation": "持有",
                "confidence": 0.3,
                "reasoning": f"决策过程中发生错误: {str(e)}",
                "error": str(e),
            }
        }


def generate_fallback_decision(symbol: str, review: Dict) -> Dict[str, Any]:
    """
    LLM 失败时的决策降级方案
    """
    sentiment = review.get("overall_sentiment", "中立")
    confidence = review.get("confidence_level", 0.5)

    # 根据情绪和信心水平做简单决策
    if "看多" in sentiment and confidence > 0.6:
        recommendation = "买入"
    elif "看空" in sentiment and confidence > 0.6:
        recommendation = "卖出"
    else:
        recommendation = "持有"

    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "target_price": "需根据具体数据确定",
        "stop_loss": "需根据具体数据确定",
        "holding_period": "3-6 个月",
        "position_size": "正常",
        "key_monitoring_points": ["股价走势", "基本面动向"],
        "exit_signals": ["大幅亏损", "基本面恶化"],
        "reasoning": f"基于综合评审（{sentiment}），给出 {recommendation} 建议。数据有限的情况下，建议谨慎决策。",
        "note": "LLM 不可用，使用简化的决策规则",
    }
