"""
Phase 3 Storage Layer v2 Verification (Using LangChain Official APIs)

Tests:
  1. LangChain SQLChatMessageHistory message persistence
  2. SessionManager and ContextManager thin wrappers
  3. Analysis metadata storage in SQLAlchemy
  4. Context injection into analysis state
"""

import json
import sys
import uuid
from datetime import datetime, timedelta

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from storage import PhaseThreeStorage, SessionManager, ContextManager, AnalysisMetadata, DB_URL


def test_storage_v2():
    """Test storage layer v2 functionality"""
    print("\n" + "="*70)
    print("🔧 Phase 3 Storage Layer v2 Verification (LangChain Official APIs)")
    print("="*70 + "\n")

    # ─── Test 1: Message History (SQLChatMessageHistory) ───────────────────
    print("[1/5] Testing SQLChatMessageHistory (LangChain Official API)...")
    try:
        session_id = str(uuid.uuid4())
        msg_history = PhaseThreeStorage.get_message_history(session_id)

        # Add messages using LangChain API
        msg_history.add_user_message("分析 600519.SH 的投资机会")
        msg_history.add_ai_message("已完成 600519.SH 的分析，建议买入...")
        msg_history.add_user_message("目标价格是多少？")
        msg_history.add_ai_message("目标价格 150 元，止损 120 元。")

        # Verify messages are persisted
        messages = msg_history.messages
        assert len(messages) >= 4, f"Expected at least 4 messages, got {len(messages)}"
        print(f"✓ Message history working: {len(messages)} messages stored in SQLite\n")
    except Exception as e:
        print(f"✗ Message history failed: {e}\n")
        return

    # ─── Test 2: SessionManager Wrapper ────────────────────────────────────
    print("[2/5] Testing SessionManager (thin wrapper around SQLChatMessageHistory)...")
    try:
        # Create new session
        session_mgr = SessionManager()
        test_session_id = session_mgr.get_session_id()
        print(f"✓ New session created: {test_session_id[:8]}...\n")

        # Test adding messages through SessionManager
        session_mgr.add_message("human", "请分析 AAPL")
        session_mgr.add_message("ai", "AAPL 目前处于上升趋势...")
        print(f"✓ Messages added through SessionManager\n")

    except Exception as e:
        print(f"✗ SessionManager test failed: {e}\n")
        return

    # ─── Test 3: Analysis Metadata Storage ─────────────────────────────────
    print("[3/5] Testing Analysis Metadata Storage (SQLAlchemy)...")
    try:
        # Create mock analysis state
        mock_state = {
            "symbol": "600519.SH",
            "initial_request": "分析 600519.SH",
            "technical_report": {"trend": "上升", "rsi": 65},
            "fundamental_report": {"pe_ratio": 15.2, "valuation": "低估"},
            "final_recommendation": {
                "recommendation": "买入",
                "confidence": 0.85,
                "target_price": 150.0,
                "stop_loss": 120.0,
                "reasoning": "技术面和基本面支持上升"
            },
            "errors": []
        }

        # Save analysis using PhaseThreeStorage
        PhaseThreeStorage.save_analysis(test_session_id, "600519.SH", mock_state)
        print(f"✓ Analysis metadata saved to database\n")

        # Retrieve analysis
        latest = PhaseThreeStorage.get_latest_analysis(test_session_id, "600519.SH")
        assert latest is not None, "Failed to retrieve analysis"
        assert latest["symbol"] == "600519.SH"
        assert latest["recommendation"] == "买入"
        assert latest["confidence"] == 0.85
        print(f"✓ Analysis retrieved successfully: {latest['recommendation']} (confidence: {latest['confidence']})\n")

    except Exception as e:
        print(f"✗ Analysis metadata test failed: {e}\n")
        return

    # ─── Test 4: Context Injection ─────────────────────────────────────────
    print("[4/5] Testing Context Injection (ContextManager)...")
    try:
        ctx_mgr = ContextManager(test_session_id)

        # Load context from session
        context = ctx_mgr.load_context()

        assert "recent_messages" in context, "Missing recent_messages in context"
        assert "recent_analyses" in context, "Missing recent_analyses in context"
        assert "context_summary" in context, "Missing context_summary in context"

        print(f"✓ Context loaded successfully:")
        print(f"  - Recent messages: {context['recent_messages']}")
        print(f"  - Recent analyses: {len(context['recent_analyses'])}")
        print(f"  - Context summary: {context['context_summary']}\n")

        # Test context injection into state
        test_state = {
            "initial_request": "继续分析...",
            "symbol": "600519.SH",
            "date_range": None,
            "planned_tasks": [],
            "historical_data": None,
            "fundamentals": None,
            "news": None,
            "technical_report": None,
            "fundamental_report": None,
            "reviewer_summary": None,
            "final_recommendation": None,
            "errors": [],
            "data_quality": None,
        }

        enriched_state = ctx_mgr.inject_context_into_state(test_state)

        # Verify context was injected
        if context['recent_analyses']:
            assert "【会话上下文】" in enriched_state.get("initial_request", ""), \
                "Context not injected into state"
            print(f"✓ Context injected into state successfully\n")
        else:
            print(f"✓ Context injection works (no recent analyses to inject)\n")

    except Exception as e:
        print(f"✗ Context injection test failed: {e}\n")
        return

    # ─── Test 5: Session Retrieval ────────────────────────────────────────
    print("[5/5] Testing Session Retrieval...")
    try:
        # Get all sessions
        all_sessions = PhaseThreeStorage.get_all_sessions()
        assert len(all_sessions) > 0, "No sessions found"
        assert test_session_id in all_sessions, f"Test session {test_session_id} not found in all_sessions"

        # Get analyses for session
        analyses = PhaseThreeStorage.get_analyses(test_session_id, limit=10)
        assert len(analyses) >= 1, "No analyses found for session"

        print(f"✓ Session retrieval working:")
        print(f"  - Total sessions: {len(all_sessions)}")
        print(f"  - Analyses in test session: {len(analyses)}")
        print(f"  - Latest analysis symbol: {analyses[0]['symbol']}\n")

    except Exception as e:
        print(f"✗ Session retrieval test failed: {e}\n")
        return

    # ─── Summary ──────────────────────────────────────────────────────────
    print("="*70)
    print("✓ All tests passed! Storage v2 working correctly")
    print("="*70)
    print(f"\n📊 Key improvements in v2:")
    print(f"  • Uses LangChain's official SQLChatMessageHistory for messages")
    print(f"  • Minimal custom code (thin wrappers only)")
    print(f"  • AnalysisMetadata table stores summaries only")
    print(f"  • Full state backed up in JSON field")
    print(f"\n📁 Database location: {DB_URL}\n")


if __name__ == "__main__":
    test_storage_v2()
