"""
LangGraph 工作流定义

工作流：
START → planner → data_fetcher → [technical, fundamental (parallel)] → reviewer → decider → END
"""

import logging
from langgraph.graph import StateGraph, START, END

from state import FinancialAnalysisState
from agents.planner import planner_agent
from agents.data_agent import data_agent
from agents.technical_agent import technical_analyst_agent
from agents.fundamental_agent import fundamental_analyst_agent
from agents.reviewer import reviewer_agent
from agents.decider import decider_agent

logger = logging.getLogger(__name__)


def build_graph():
    """
    构建 LangGraph 工作流

    节点：
    1. planner: 解析请求，提取股票代码和日期范围
    2. data_fetcher: 获取历史数据、基本面、新闻
    3. technical_analyst: 技术面分析（与 fundamental 并行）
    4. fundamental_analyst: 基本面分析（与 technical 并行）
    5. reviewer: 综合两份报告
    6. decider: 生成最终建议

    边：
    - START → planner
    - planner → data_fetcher
    - data_fetcher → technical_analyst (并行)
    - data_fetcher → fundamental_analyst (并行)
    - technical_analyst → reviewer (隐式 join)
    - fundamental_analyst → reviewer (隐式 join)
    - reviewer → decider
    - decider → END
    """
    workflow = StateGraph(FinancialAnalysisState)

    # 添加节点
    workflow.add_node("planner", planner_agent)
    workflow.add_node("data_fetcher", data_agent)
    workflow.add_node("technical_analyst", technical_analyst_agent)
    workflow.add_node("fundamental_analyst", fundamental_analyst_agent)
    workflow.add_node("reviewer", reviewer_agent)
    workflow.add_node("decider", decider_agent)

    # 添加边
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "data_fetcher")

    # 并行分支
    workflow.add_edge("data_fetcher", "technical_analyst")
    workflow.add_edge("data_fetcher", "fundamental_analyst")

    # 合并点（reviewer 有两个入边，LangGraph 会自动等待）
    workflow.add_edge("technical_analyst", "reviewer")
    workflow.add_edge("fundamental_analyst", "reviewer")

    # 最终路径
    workflow.add_edge("reviewer", "decider")
    workflow.add_edge("decider", END)

    app = workflow.compile()
    return app
