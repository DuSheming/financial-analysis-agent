"""
Planner Agent - 解析用户请求并分解任务

负责：
1. 提取股票代码
2. 确定分析周期
3. 分解分析任务
"""

import json
import re
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config import llm_config
from state import FinancialAnalysisState
from tools.data_tools import validate_symbol

logger = logging.getLogger(__name__)


def _parse_json_output(text: str) -> Dict[str, Any]:
    """健壮的 JSON 解析：处理 LLM 可能返回 Markdown 代码块的情况"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Unable to parse JSON from output")


def planner_agent(state: FinancialAnalysisState) -> Dict[str, Any]:
    """
    解析用户请求并制定分析计划

    输入：initial_request (如："分析600519.SH的长期投资价值")
    输出：symbol, date_range, planned_tasks
    """
    try:
        request = state["initial_request"]
        logger.info(f"Planner: Processing request: {request[:100]}...")

        # 构建提示词
        prompt_text = """你是一个专业的金融分析师。请分析用户的请求，并返回 JSON 格式的结果。

用户请求：{request}

请只返回 JSON 对象，不要包含任何其他文字或 Markdown 代码块：
{{
    "symbol": "股票代码 (如 600519.SH)",
    "date_range": {{
        "start": "YYYY-MM-DD 格式开始日期",
        "end": "YYYY-MM-DD 格式结束日期"
    }},
    "analysis_type": "short_term|medium_term|long_term",
    "tasks": ["任务1", "任务2", "任务3"]
}}

分析说明：
- 如果用户没有指定日期，假设：short_term=3个月, medium_term=6个月, long_term=1年
- 股票代码格式：A股 (600519.SH), 港股 (0700.HK), 美股 (AAPL)
- 返回具体的开始和结束日期
"""

        template = ChatPromptTemplate.from_template(prompt_text)
        llm = llm_config.get_llm(temperature=llm_config.DEFAULT_TEMPERATURES["planner"])
        chain = template | llm | StrOutputParser()

        raw_output = chain.invoke({"request": request})
        result = _parse_json_output(raw_output)

        # 验证股票代码
        symbol = result.get("symbol", "").upper().strip()
        if not validate_symbol(symbol):
            return {
                "symbol": "UNKNOWN",
                "date_range": None,
                "planned_tasks": [],
                "errors": [f"Invalid stock symbol: {symbol}. Please provide A-share (600519.SH), HK stock (0700.HK) or US stock (AAPL)."],
            }

        # 验证日期
        date_range = result.get("date_range", {})
        try:
            start = datetime.strptime(date_range.get("start", ""), "%Y-%m-%d")
            end = datetime.strptime(date_range.get("end", ""), "%Y-%m-%d")
        except:
            # 默认日期范围：过去一年
            end = datetime.now()
            start = end - timedelta(days=365)
            date_range = {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d"),
            }

        tasks = result.get("tasks", [
            "获取历史价格和基本面数据",
            "进行技术分析",
            "进行基本面分析",
            "综合两份报告",
            "生成最终建议",
        ])

        logger.info(f"Planner: Symbol={symbol}, DateRange={date_range}, Tasks={len(tasks)}")

        return {
            "symbol": symbol,
            "date_range": date_range,
            "planned_tasks": tasks,
            "errors": [],
        }

    except Exception as e:
        logger.error(f"Planner error: {e}")
        return {
            "symbol": "UNKNOWN",
            "date_range": None,
            "planned_tasks": [],
            "errors": [f"Planning failed: {str(e)}"],
        }
