"""
Phase 3 Storage Layer Verification Script
"""

import json
import sys
from datetime import datetime, timedelta

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 初始化数据库
from storage import init_database, SessionRepository, AnalysisRepository, MessageRepository
from services import SessionManager, ContextManager


def test_storage_layer():
    """测试存储层功能"""
    print("\n" + "="*60)
    print("🔧 Phase 3 存储层验证")
    print("="*60 + "\n")

    # ─── 测试 1: 数据库初始化 ────────────────────────────────────────
    print("[1/6] 初始化数据库...")
    try:
        init_database()
        print("✓ 数据库初始化成功\n")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}\n")
        return

    # ─── 测试 2: 会话管理 ──────────────────────────────────────────
    print("[2/6] 测试会话管理...")
    try:
        session_mgr = SessionManager()
        session_id = session_mgr.get_session_id()
        print(f"✓ 创建新会话: {session_id[:8]}...\n")
    except Exception as e:
        print(f"✗ 会话创建失败: {e}\n")
        return

    # ─── 测试 3: 保存分析结果 ────────────────────────────────────────
    print("[3/6] 测试分析保存...")
    try:
        # 创建模拟的分析状态
        mock_state = {
            "initial_request": "分析股票 600519.SH",
            "symbol": "600519.SH",
            "technical_report": {"trend": "上升趋势", "rsi": 65},
            "fundamental_report": {"pe_ratio": 15.2, "valuation": "低估"},
            "final_recommendation": {
                "recommendation": "买入",
                "confidence": 0.85,
                "target_price": 150.0,
                "stop_loss": 120.0,
                "reasoning": "技术面和基本面都支持上升空间"
            },
            "errors": []
        }

        today = datetime.now()
        start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        analysis = session_mgr.save_analysis(
            symbol="600519.SH",
            date_range_start=start_date,
            date_range_end=end_date,
            state=mock_state
        )
        print(f"✓ 分析已保存: {analysis.analysis_id[:8]}...\n")
    except Exception as e:
        print(f"✗ 分析保存失败: {e}\n")
        return

    # ─── 测试 4: 消息历史 ────────────────────────────────────────────
    print("[4/6] 测试消息记录...")
    try:
        MessageRepository.add(
            session_id=session_id,
            message_type="human",
            content="请分析 600519.SH 的投资前景"
        )
        MessageRepository.add(
            session_id=session_id,
            message_type="ai",
            content="根据技术分析和基本面数据，600519.SH 目前处于上升趋势..."
        )
        msg_count = MessageRepository.count_by_session(session_id)
        print(f"✓ 已记录 {msg_count} 条消息\n")
    except Exception as e:
        print(f"✗ 消息记录失败: {e}\n")
        return

    # ─── 测试 5: 上下文管理 ──────────────────────────────────────────
    print("[5/6] 测试上下文管理...")
    try:
        ctx_mgr = ContextManager(session_id)
        context = ctx_mgr.load_context()

        print(f"✓ 上下文加载成功")
        print(f"  - 最近消息: {len(context['recent_messages'])} 条")
        print(f"  - 最近分析: {len(context['recent_analyses'])} 次")
        print(f"  - 预估 Token: {context['context_tokens_estimate']}")
        print()
    except Exception as e:
        print(f"✗ 上下文管理失败: {e}\n")
        return

    # ─── 测试 6: 会话检索 ────────────────────────────────────────────
    print("[6/6] 测试会话检索...")
    try:
        # 加载已有会话
        loaded_mgr = SessionManager(session_id)
        info = loaded_mgr.get_session_info()
        analyses = loaded_mgr.get_analyses()

        print(f"✓ 会话加载成功: {info['title']}")
        print(f"  - 分析数: {len(analyses)}")
        print(f"  - 创建时间: {info['created_at']}")
        print()
    except Exception as e:
        print(f"✗ 会话检索失败: {e}\n")
        return

    # ─── 总结 ──────────────────────────────────────────────────────
    print("="*60)
    print("✓ 所有测试通过！Storage 层功能正常")
    print("="*60 + "\n")

    # 显示数据库路径
    from storage.database import DB_PATH
    print(f"📁 数据库位置: {DB_PATH}\n")


if __name__ == "__main__":
    test_storage_layer()
