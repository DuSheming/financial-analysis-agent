"""
智能对话式交互系统 - 简化版，不依赖 langgraph.prebuilt

使用 LLM 直接调用工具，支持自然语言对话。
"""

import json
import uuid
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

from config import llm_config
from storage import SessionManager, ContextManager, PhaseThreeStorage
from state import FinancialAnalysisState
from graph import build_graph
from report_generator import export_report

console = Console()


# ============ LangChain Tools ============


@tool
def analyze_stock(symbol: str, days: int = 365, formats: str = "markdown,html") -> str:
    """分析股票

    Args:
        symbol: 股票代码，如 "600519.SH" 或 "600519"
        days: 分析周期，默认 365 天
        formats: 输出格式，默认 "markdown,html"

    Returns:
        分析结果摘要
    """
    try:
        if not symbol.endswith((".SH", ".SZ")):
            symbol = symbol.upper() + ".SH"

        session_mgr = SessionManager()
        current_session_id = session_mgr.get_session_id()
        ctx_mgr = ContextManager(current_session_id)

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        request = f"分析股票 {symbol}，时间范围 {days} 天"
        initial_state = FinancialAnalysisState(
            initial_request=request,
            planned_tasks=[],
            symbol=symbol,
            date_range={"start": start_date, "end": end_date},
            historical_data=None,
            fundamentals=None,
            news=None,
            technical_report=None,
            fundamental_report=None,
            reviewer_summary=None,
            final_recommendation=None,
            errors=[],
            data_quality=None,
        )

        initial_state = ctx_mgr.inject_context_into_state(initial_state)

        console.print(f"[cyan]📊 正在分析 {symbol}...[/cyan]")
        app = build_graph()
        final_state = app.invoke(initial_state)

        session_mgr.save_analysis(symbol, final_state)

        fmt_list = [f.strip() for f in formats.split(",") if f.strip()]
        report_paths = export_report(final_state, fmt_list)

        rec = final_state.get("final_recommendation", {})
        tech = final_state.get("technical_report", {})
        fund = final_state.get("fundamental_report", {})

        summary = f"""## 📊 {symbol} 分析完成

| 指标 | 值 |
|------|-----|
| **推荐** | **{rec.get('recommendation', 'N/A')}** |
| 置信度 | {int(rec.get('confidence', 0) * 100)}% |
| 目标价 | ${rec.get('target_price', 'N/A')} |

📈 技术面: {tech.get('trend', 'N/A')}
💰 基本面: {fund.get('valuation_assessment', 'N/A')}"""
        return summary

    except Exception as e:
        return f"❌ 分析失败: {str(e)}"


@tool
def view_reports(limit: int = 10) -> str:
    """查看最近生成的报告"""
    import os

    reports_dir = Path("./reports")
    if not reports_dir.exists():
        return "📁 还没有生成任何报告"

    all_files = []
    for root, dirs, files in os.walk(reports_dir):
        for file in files:
            try:
                filepath = Path(root) / file
                mtime = filepath.stat().st_mtime
                all_files.append((filepath, mtime))
            except:
                pass

    if not all_files:
        return "📁 没有找到报告文件"

    all_files.sort(key=lambda x: x[1], reverse=True)

    result = f"## 📋 最近的报告 (共 {len(all_files)} 个)\n\n"
    for filepath, mtime in all_files[:limit]:
        rel_path = filepath.relative_to(reports_dir)
        mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        result += f"- `{rel_path}` ({mtime_str})\n"

    return result


@tool
def manage_sessions(action: str) -> str:
    """管理会话 (list|info)"""
    try:
        if action == "list":
            sessions = PhaseThreeStorage.get_all_sessions()
            if not sessions:
                return "还没有任何会话"

            result = f"## 📌 所有会话 (共 {len(sessions)} 个)\n\n"
            for sid in sessions[:10]:
                analyses = PhaseThreeStorage.get_analyses(sid, limit=3)
                result += f"- `{sid[:8]}...`: "
                if analyses:
                    result += ", ".join(
                        f"{a['symbol']}:{a['recommendation']}" for a in analyses
                    )
                result += "\n"
            return result
        else:
            return "请用 'list' 查看所有会话"

    except Exception as e:
        return f"❌ 操作失败: {str(e)}"


@tool
def ask_question(question: str) -> str:
    """回答财务问题"""
    try:
        llm = llm_config.get_llm(temperature=0.7)
        response = llm.invoke(f"用中文回答这个财务分析问题:\n\n{question}")
        return response.content
    except Exception as e:
        return f"❌ 无法回答: {str(e)}"


# ============ 对话式 CLI ============


class SmartInteractiveCLI:
    """基于 LLM 的智能对话交互系统"""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.session_manager = SessionManager(self.session_id)
        self.llm = llm_config.get_llm(temperature=0.7)
        self.chat_history = []
        self.tools = {
            "analyze_stock": analyze_stock,
            "view_reports": view_reports,
            "manage_sessions": manage_sessions,
            "ask_question": ask_question,
        }

    def _parse_and_call_tool(self, user_input: str) -> Optional[str]:
        """用 LLM 解析用户意图并调用工具"""
        system_prompt = """你是一个财务分析助手。根据用户输入，决定是否调用工具。

可用工具:
1. analyze_stock(symbol, days) - 分析股票
2. view_reports(limit) - 查看报告
3. manage_sessions(action) - 管理会话
4. ask_question(question) - 回答问题

如果需要调用工具，请用这个格式回复:
TOOL_CALL: {"tool": "工具名", "params": {...}}

如果不需要调用工具（普通对话），直接回复内容即可。"""

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        for msg in self.chat_history[-4:]:  # 最多 2 轮历史
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages.append({"role": "assistant", "content": msg.content})

        messages.append({"role": "user", "content": user_input})

        response = self.llm.invoke(messages)
        text = response.content

        # 检查是否有工具调用
        if "TOOL_CALL:" in text:
            try:
                json_str = text.split("TOOL_CALL:")[1].strip()
                tool_call = json.loads(json_str)
                tool_name = tool_call.get("tool")
                params = tool_call.get("params", {})

                if tool_name in self.tools:
                    tool_func = self.tools[tool_name]
                    result = tool_func.invoke(params)
                    return result
            except Exception:
                pass

        # 不调用工具，直接回复
        return text

    def chat(self, user_input: str) -> None:
        """处理用户输入"""
        console.print(f"\n[bold cyan]You:[/bold cyan] {user_input}\n")

        try:
            with console.status("[bold green]思考中...[/bold green]"):
                output = self._parse_and_call_tool(user_input)

            if output is None:
                output = "（无响应）"

            # 更新对话历史
            self.chat_history.append(HumanMessage(content=user_input))
            self.chat_history.append(AIMessage(content=output))
            if len(self.chat_history) > 40:
                self.chat_history = self.chat_history[-40:]

            console.print(f"\n[bold green]Assistant:[/bold green]\n")
            try:
                console.print(Markdown(output))
            except:
                console.print(output)
            console.print()

            # 持久化
            try:
                msg_history = PhaseThreeStorage.get_message_history(self.session_id)
                msg_history.add_user_message(user_input)
                msg_history.add_ai_message(output)
            except:
                pass

        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")

    def run(self):
        """主对话循环"""
        console.print(
            """
[bold cyan]╔════════════════════════════════════════╗
║  💬  智能财务分析对话助手                ║
║  Powered by LangChain                  ║
╚════════════════════════════════════════╝[/bold cyan]

📝 使用自然语言进行对话。例如：
  • "帮我分析 600519.SH"
  • "查看我生成的所有报告"
  • "什么是 PE 比率？"
  • "退出" 来结束对话
"""
        )

        while True:
            user_input = Prompt.ask("\n[cyan]You[/cyan]").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "退出", "q"]:
                console.print("\n[yellow]👋 再见！[/yellow]")
                break

            self.chat(user_input)


def run_smart_interactive(session_id: Optional[str] = None):
    """启动智能对话式交互"""
    cli = SmartInteractiveCLI(session_id)
    cli.run()
