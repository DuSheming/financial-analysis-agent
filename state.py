"""
增强的 LangGraph 状态定义

所有字段都应是不可变的，Agent 返回新值而非修改现有值。
"""

from typing import TypedDict, List, Optional, Dict, Any


class FinancialAnalysisState(TypedDict):
    """
    金融分析工作流状态

    字段说明：
    - initial_request: 用户的初始分析请求
    - planned_tasks: Planner 分解的任务列表
    - symbol: 股票代码 (e.g., "600519.SH")
    - date_range: 分析周期 {"start": "2024-01-01", "end": "2025-02-18"}
    - historical_data: JSON 格式的 OHLCV 历史数据
    - fundamentals: 基本面数据 dict
    - news: 新闻列表
    - technical_report: 技术分析报告
    - fundamental_report: 基本面分析报告
    - reviewer_summary: 综合评审报告
    - final_recommendation: 最终投资建议
    - errors: 错误追踪（支持优雅降级）
    - data_quality: 数据质量评分
    """

    # 基础信息
    initial_request: str
    planned_tasks: List[str]
    symbol: str
    date_range: Optional[Dict[str, str]]

    # 数据层
    historical_data: Optional[str]  # JSON 格式
    fundamentals: Optional[Dict[str, Any]]
    news: Optional[List[Dict[str, str]]]

    # 分析报告
    technical_report: Optional[Dict[str, Any]]
    fundamental_report: Optional[Dict[str, Any]]
    reviewer_summary: Optional[Dict[str, Any]]
    final_recommendation: Optional[Dict[str, Any]]

    # 质量与错误追踪
    errors: List[str]
    data_quality: Optional[Dict[str, Any]]
