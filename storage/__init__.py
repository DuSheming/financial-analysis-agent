"""
Storage Module (Phase 3 v2)

使用 LangChain 官方 API:
  - SQLChatMessageHistory: 对话历史
  - SQLAlchemy: 只存分析元数据

废弃了自己写的 Repository 模式
"""

from storage.storage_v2 import (
    PhaseThreeStorage,
    SessionManager,
    ContextManager,
    AnalysisMetadata,
    DB_URL,
)

__all__ = [
    "PhaseThreeStorage",
    "SessionManager",
    "ContextManager",
    "AnalysisMetadata",
    "DB_URL",
]
