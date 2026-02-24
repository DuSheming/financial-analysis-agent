"""
Reviewer Agent - 综合评审

负责：
1. 检查技术面和基本面是否矛盾
2. 权衡两份报告的重要程度
3. 输出综合评审报告
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


REVIEWER_PROMPT = """你是一位资深的投资评审专家。请对以下技术分析和基本面分析进行综合评审。

股票代码: {symbol}

## 技术分析报告
{technical_report}

## 基本面分析报告
{fundamental_report}

## 评审要求

请以 **JSON 格式返回以下结构，不要包含任何其他文字或 Markdown 代码块**：

{{
    "contradictions": [
        {{
            "area": "矛盾所在领域",
            "technical_view": "技术面观点",
            "fundamental_view": "基本面观点",
            "resolution": "如何理解这个矛盾",
            "severity": "高/中/低"
        }}
    ],
    "consensus_level": "高度共识/部分共识/低共识",
    "weighted_assessment": {{
        "bullish_factors": ["看多因素列表"],
        "bearish_factors": ["看空因素列表"],
        "neutral_factors": ["中立因素列表"]
    }},
    "key_risk": "最主要的风险是什么",
    "key_opportunity": "最主要的机会是什么",
    "overall_sentiment": "强烈看多/看多/中立/看空/强烈看空",
    "confidence_level": 0.75,
    "executive_summary": "200字以内的综合评述，应该包含对矛盾的说明和最终倾向"
}}
"""


def reviewer_agent(state: FinancialAnalysisState) -> Dict[str, Any]:
    """
    综合评审

    输入：technical_report, fundamental_report
    输出：reviewer_summary
    """
    try:
        symbol = state.get("symbol", "UNKNOWN")
        tech_report = state.get("technical_report")
        fund_report = state.get("fundamental_report")

        logger.info(f"Reviewer: Consolidating reports for {symbol}")

        # 处理缺失的报告
        if not tech_report:
            tech_report = {"error": "No technical analysis available"}
        if not fund_report:
            fund_report = {"error": "No fundamental analysis available"}

        # LLM 综合评审
        logger.info(f"Reviewer: Invoking LLM for {symbol}...")

        try:
            template = ChatPromptTemplate.from_template(REVIEWER_PROMPT)
            llm = llm_config.get_llm(temperature=llm_config.DEFAULT_TEMPERATURES["analyst"])
            chain = template | llm | StrOutputParser()

            raw_output = chain.invoke({
                "symbol": symbol,
                "technical_report": json.dumps(tech_report, ensure_ascii=False),
                "fundamental_report": json.dumps(fund_report, ensure_ascii=False),
            })

            logger.debug(f"Reviewer raw LLM output:\n{raw_output[:500]}...")
            result = _parse_json_output(raw_output)
        except Exception as llm_e:
            logger.warning(f"LLM call failed, using fallback review: {llm_e}")
            logger.debug(f"Raw output that failed to parse: {raw_output[:1000] if 'raw_output' in locals() else 'N/A'}")
            result = generate_fallback_review(symbol, tech_report, fund_report)

        logger.info(f"Reviewer: Completed for {symbol}")
        return {"reviewer_summary": result}

    except Exception as e:
        logger.error(f"Reviewer error: {e}")
        return {
            "reviewer_summary": {
                "contradictions": [],
                "consensus_level": "低共识",
                "overall_sentiment": "中立",
                "executive_summary": f"评审过程中发生错误: {str(e)}",
                "error": str(e),
            }
        }


def generate_fallback_review(
    symbol: str, tech_report: Dict, fund_report: Dict
) -> Dict[str, Any]:
    """
    LLM 失败时的评审降级方案
    """
    contradictions = []

    # 简单的矛盾检测
    tech_signal = tech_report.get("short_term_signal", "持有")
    fund_growth = fund_report.get("growth_potential", "中")

    if tech_signal == "卖出" and fund_growth == "强":
        contradictions.append({
            "area": "短期技术 vs 长期基本面",
            "technical_view": "卖出信号",
            "fundamental_view": "强劲增长",
            "resolution": "短期调整，长期看好",
            "severity": "中",
        })

    return {
        "contradictions": contradictions,
        "consensus_level": "部分共识",
        "overall_sentiment": "中立",
        "weighted_assessment": {
            "bullish_factors": [fund_report.get("summary", "")[:30]],
            "bearish_factors": [tech_report.get("summary", "")[:30]],
        },
        "executive_summary": "数据有限的情况下，建议以基本面为主，技术面作为参考。",
        "note": "LLM 不可用，使用简化的评审逻辑",
        "confidence_level": 0.5,
    }
