"""
Phase 3 精简版本 - 使用 LangChain 官方 API

只用 SQLChatMessageHistory + 最小化自己的代码
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from langchain_community.chat_message_histories import SQLChatMessageHistory
from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

# ============ 数据库配置 ============

DB_PATH = Path(__file__).parent.parent / "agent.db"
DB_URL = f"sqlite:///{DB_PATH.as_posix()}"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ============ 只保留分析元数据表 ============

class AnalysisMetadata(Base):
    """分析元数据 - 只保留摘要信息"""
    __tablename__ = "analysis_metadata"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    recommendation = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    date_analyzed = Column(DateTime, default=datetime.utcnow, index=True)
    full_state = Column(JSON, nullable=True)  # 完整 state 作为 backup

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "symbol": self.symbol,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "date_analyzed": self.date_analyzed.isoformat(),
        }


# 创建表
Base.metadata.create_all(engine)


# ============ 简化的 Session 和 Message 管理 ============

class PhaseThreeStorage:
    """用官方 LangChain API 管理 Phase 3"""

    @staticmethod
    def get_message_history(session_id: str):
        """获取对话历史 - 直接用 LangChain 的！"""
        return SQLChatMessageHistory(
            session_id=session_id,
            connection=engine,  # 使用新的参数名（替代已弃用的 connection_string）
        )

    @staticmethod
    def save_analysis(
        session_id: str,
        symbol: str,
        state: Dict[str, Any],
    ) -> None:
        """保存分析元数据"""
        rec = state.get("final_recommendation") or {}

        db = SessionLocal()
        try:
            metadata = AnalysisMetadata(
                session_id=session_id,
                symbol=symbol.upper(),
                recommendation=rec.get("recommendation", "N/A"),
                confidence=float(rec.get("confidence", 0.0)),
                target_price=_safe_float(rec.get("target_price")),
                stop_loss=_safe_float(rec.get("stop_loss")),
                full_state=_sanitize_state(state),  # 备份完整 state
            )
            db.add(metadata)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def get_analyses(session_id: str, limit: int = 10) -> List[Dict]:
        """获取会话内的所有分析"""
        db = SessionLocal()
        try:
            analyses = (
                db.query(AnalysisMetadata)
                .filter(AnalysisMetadata.session_id == session_id)
                .order_by(AnalysisMetadata.date_analyzed.desc())
                .limit(limit)
                .all()
            )
            return [a.to_dict() for a in analyses]
        finally:
            db.close()

    @staticmethod
    def get_latest_analysis(session_id: str, symbol: str) -> Optional[Dict]:
        """获取最新的分析"""
        db = SessionLocal()
        try:
            analysis = (
                db.query(AnalysisMetadata)
                .filter(
                    AnalysisMetadata.session_id == session_id,
                    AnalysisMetadata.symbol == symbol.upper(),
                )
                .order_by(AnalysisMetadata.date_analyzed.desc())
                .first()
            )
            return analysis.to_dict() if analysis else None
        finally:
            db.close()

    @staticmethod
    def get_all_sessions() -> List[str]:
        """获取所有会话 ID"""
        db = SessionLocal()
        try:
            sessions = db.query(AnalysisMetadata.session_id).distinct().all()
            return [s[0] for s in sessions]
        finally:
            db.close()


# ============ 会话管理器（简化版） ============

class SessionManager:
    """极简会话管理"""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.message_history = PhaseThreeStorage.get_message_history(self.session_id)

    def get_session_id(self) -> str:
        return self.session_id

    def save_analysis(self, symbol: str, state: Dict[str, Any]) -> None:
        """保存分析"""
        PhaseThreeStorage.save_analysis(self.session_id, symbol, state)

    def get_message_history(self):
        """获取消息历史"""
        return self.message_history

    def add_message(self, role: str, content: str) -> None:
        """添加消息到历史"""
        if role == "human":
            self.message_history.add_user_message(content)
        elif role == "ai":
            self.message_history.add_ai_message(content)
        elif role == "system":
            self.message_history.add_ai_message(f"[System] {content}")


# ============ 上下文管理器（简化版） ============

class ContextManager:
    """极简上下文管理"""

    MAX_CONTEXT_CHARS = 40000

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.message_history = PhaseThreeStorage.get_message_history(session_id)

    def load_context(self) -> Dict[str, Any]:
        """加载会话上下文"""
        # 获取最近的消息
        messages = self.message_history.messages[-10:]  # 最近 10 条

        # 获取最近的分析
        analyses = PhaseThreeStorage.get_analyses(self.session_id, limit=3)

        # 构建摘要
        context_summary = self._build_summary(analyses)

        return {
            "recent_messages": len(messages),
            "recent_analyses": analyses,
            "context_summary": context_summary,
        }

    def inject_context_into_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """注入上下文到状态"""
        context = self.load_context()

        if context["recent_analyses"]:
            summary = self._format_analyses(context["recent_analyses"])
            context_prompt = f"\n\n【会话上下文】\n已分析的股票:\n{summary}\n请参考之前的分析。"
            state["initial_request"] = state.get("initial_request", "") + context_prompt

        return state

    def add_message(self, role: str, content: str) -> None:
        """添加消息"""
        if role == "human":
            self.message_history.add_user_message(content)
        elif role == "ai":
            self.message_history.add_ai_message(content)

    def _build_summary(self, analyses: List[Dict]) -> str:
        """构建上下文摘要"""
        if not analyses:
            return ""

        symbols = set(a["symbol"] for a in analyses)
        summary = f"已分析: {', '.join(symbols)}"

        if analyses:
            latest = analyses[0]
            summary += f" | 最新: {latest['symbol']} → {latest['recommendation']}"

        return summary

    def _format_analyses(self, analyses: List[Dict]) -> str:
        """格式化分析列表"""
        lines = []
        for a in analyses:
            lines.append(
                f"- {a['symbol']}: {a['recommendation']} "
                f"(置信度 {int(a.get('confidence', 0) * 100)}%)"
            )
        return "\n".join(lines)


# ============ 内部工具函数 ============

def _safe_float(value: Any) -> Optional[float]:
    """安全转换为 float"""
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _sanitize_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """清理状态以便 JSON 存储"""
    sanitized = {k: v for k, v in state.items()}

    # 截断过大的历史数据
    if "historical_data" in sanitized and sanitized["historical_data"]:
        data = sanitized["historical_data"]
        if isinstance(data, str) and len(data) > 50000:
            sanitized["historical_data"] = data[:50000] + "...[truncated]"

    return sanitized
