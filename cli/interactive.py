"""
交互式命令行菜单

支持单只股票分析、历史报告查看、会话管理
"""

import os
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.live import Live
from rich.text import Text

from config import llm_config
from state import FinancialAnalysisState
from graph import build_graph
from report_generator import export_report
from storage import SessionManager, ContextManager, PhaseThreeStorage

console = Console()

AGENT_LABELS = {
    "planner": "规划 - 解析请求",
    "data_fetcher": "数据 - 获取行情",
    "technical_analyst": "分析 - 技术面",
    "fundamental_analyst": "分析 - 基本面",
    "reviewer": "评审 - 综合报告",
    "decider": "决策 - 最终建议",
}

REPORTS_DIR = Path("./reports")


# ============ 菜单入口 ============

def run_interactive():
    """运行交互式主菜单"""
    _show_banner()

    while True:
        choice = _main_menu()

        if choice == "1":
            analyze_single_stock()
        elif choice == "2":
            view_history()
        elif choice == "3":
            manage_sessions()
        elif choice == "q":
            console.print("\n[bold cyan]感谢使用，再见！[/bold cyan]\n")
            break


def _show_banner():
    """显示欢迎信息"""
    banner = Panel.fit(
        Text.from_markup(
            "[bold cyan]AI 金融分析系统[/bold cyan]\n"
            "[dim]由 LangChain + LangGraph 驱动[/dim]"
        ),
        border_style="cyan",
        padding=(1, 4),
    )
    console.print()
    console.print(banner)
    console.print(f"[dim]当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}[/dim]\n")


def _main_menu() -> str:
    """显示主菜单，返回用户选择"""
    console.print("[bold]请选择操作:[/bold]")
    console.print("  [cyan][1][/cyan] 分析股票")
    console.print("  [cyan][2][/cyan] 查看历史报告")
    console.print("  [cyan][3][/cyan] 管理会话")
    console.print("  [cyan][q][/cyan] 退出\n")

    return Prompt.ask("请输入", choices=["1", "2", "3", "q"], default="1")


# ============ 股票分析 ============

def analyze_single_stock():
    """交互式：分析单只股票"""
    console.print("\n[bold]── 分析股票 ──[/bold]\n")

    # 选择或创建会话
    session_id = _select_or_create_session()
    if not session_id:
        return

    # 输入股票代码
    symbol = _prompt_symbol()
    if not symbol:
        return

    # 选择分析时间范围
    days = _prompt_days()

    # 选择输出格式
    formats = _prompt_formats()

    # 确认
    _show_config_summary(symbol, days, formats)
    if not Confirm.ask("确认开始分析?", default=True):
        console.print("[dim]已取消[/dim]")
        return

    # 执行分析
    console.print()
    state = _run_analysis_with_progress(session_id, symbol, days)

    if state is None:
        console.print("[red]分析失败，请检查日志。[/red]")
        return

    # 生成报告
    console.print("\n[bold cyan]正在生成报告...[/bold cyan]")
    report_paths = _generate_reports(state, formats)

    # 展示结果
    _show_final_summary(state)
    _show_report_paths(report_paths)

    # 询问打开浏览器
    if "html" in report_paths:
        if Confirm.ask("\n在浏览器中打开 HTML 报告?", default=True):
            webbrowser.open(report_paths["html"].as_uri())

    console.print()


def _prompt_symbol() -> Optional[str]:
    """提示输入股票代码"""
    console.print("[dim]格式示例: 600519.SH（A股） / 0700.HK（港股） / AAPL（美股）[/dim]")
    symbol = Prompt.ask("输入股票代码").strip().upper()

    if not symbol:
        console.print("[red]股票代码不能为空[/red]")
        return None

    return symbol


def _prompt_days() -> int:
    """提示选择时间范围"""
    console.print("\n[bold]选择分析时间范围:[/bold]")
    console.print("  [1] 3 个月")
    console.print("  [2] 6 个月")
    console.print("  [3] 1 年 (默认)")
    console.print("  [4] 2 年")

    choice = Prompt.ask("请选择", choices=["1", "2", "3", "4"], default="3")
    return {"1": 90, "2": 180, "3": 365, "4": 730}[choice]


def _prompt_formats() -> List[str]:
    """提示选择输出格式"""
    console.print("\n[bold]选择输出格式:[/bold]")
    console.print("  [1] 全部（MD + HTML + JSON）(默认)")
    console.print("  [2] 仅 HTML")
    console.print("  [3] 仅 Markdown")
    console.print("  [4] 仅 JSON")

    choice = Prompt.ask("请选择", choices=["1", "2", "3", "4"], default="1")
    return {
        "1": ["md", "html", "json"],
        "2": ["html"],
        "3": ["md"],
        "4": ["json"],
    }[choice]


def _show_config_summary(symbol: str, days: int, formats: List[str]):
    """展示分析配置摘要"""
    table = Table(title="分析配置确认", box=None)
    table.add_column("配置项", style="cyan")
    table.add_column("值", style="white")

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    provider = os.getenv("LLM_PROVIDER", "未配置")
    model_env = f"{provider.upper()}_MODEL"
    model = os.getenv(model_env, "默认")

    table.add_row("股票代码", symbol)
    table.add_row("分析周期", f"{start_date} 至 {end_date}（{days}天）")
    table.add_row("输出格式", " + ".join(f.upper() for f in formats))
    table.add_row("使用模型", f"{provider} / {model}")

    console.print()
    console.print(table)
    console.print()


def _run_analysis_with_progress(session_id: str, symbol: str, days: int) -> Optional[FinancialAnalysisState]:
    """执行 LangGraph 分析，显示进度"""
    from datetime import timedelta

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    request = f"分析股票 {symbol}，分析周期从 {start_date} 到 {end_date}。"

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

    try:
        # 加载会话上下文
        session_mgr = SessionManager(session_id)
        ctx_mgr = ContextManager(session_id)

        # 注入历史上下文
        initial_state = ctx_mgr.inject_context_into_state(initial_state)

        app = build_graph()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task(f"分析 {symbol}...", total=6)

            # 利用 stream_mode 观察每个节点
            final_state = None
            node_count = 0

            for chunk in app.stream(initial_state, stream_mode="updates"):
                node_name = list(chunk.keys())[0]
                label = AGENT_LABELS.get(node_name, node_name)
                node_count += 1
                progress.update(task, advance=1, description=f"✓ {label}")
                final_state = chunk[node_name]

            # 合并最终状态
            final_state = app.invoke(initial_state) if final_state is None else \
                          _merge_state(initial_state, app, symbol, start_date, end_date)

        # 保存分析结果到数据库
        session_mgr.save_analysis(symbol, final_state)
        ctx_mgr.add_message("ai", f"已完成 {symbol} 的分析")

        return final_state

    except Exception as e:
        console.print(f"[red]分析出错: {e}[/red]")
        return None


def _merge_state(initial: FinancialAnalysisState, app, symbol: str,
                 start_date: str, end_date: str) -> FinancialAnalysisState:
    """直接 invoke 获取最终合并状态"""
    return app.invoke(initial)


def _generate_reports(state: FinancialAnalysisState, formats: List[str]) -> Dict[str, Path]:
    """生成报告文件"""
    try:
        return export_report(state, formats, REPORTS_DIR)
    except Exception as e:
        console.print(f"[red]报告生成失败: {e}[/red]")
        return {}


# ============ 结果展示 ============

def _show_final_summary(state: FinancialAnalysisState):
    """在终端显示最终摘要"""
    rec = state.get("final_recommendation") or {}
    tech = state.get("technical_report") or {}
    fund = state.get("fundamental_report") or {}
    review = state.get("reviewer_summary") or {}
    symbol = state.get("symbol", "UNKNOWN")

    recommendation = rec.get("recommendation", "N/A")
    rec_color = "green" if "买" in recommendation else \
                "red" if "卖" in recommendation else "yellow"

    table = Table(title=f"{symbol} 分析结果", border_style="dim")
    table.add_column("维度", style="cyan", min_width=14)
    table.add_column("结果", style="white")

    table.add_row("最终建议", f"[bold {rec_color}]{recommendation}[/bold {rec_color}]")
    table.add_row("置信度", f"{int(rec.get('confidence', 0) * 100)}%")
    table.add_row("目标价格", str(rec.get("target_price", "N/A")))
    table.add_row("止损价", str(rec.get("stop_loss", "N/A")))
    table.add_row("持有周期", str(rec.get("holding_period", "N/A")))
    table.add_row("技术趋势", str(tech.get("trend", "N/A")))
    table.add_row("估值评估", str(fund.get("valuation_assessment", "N/A")))
    table.add_row("整体情绪", str(review.get("overall_sentiment", "N/A")))

    errors = state.get("errors", [])
    if errors:
        table.add_row("[yellow]注意[/yellow]", f"{len(errors)} 项警告")

    console.print()
    console.print(table)


def _show_report_paths(report_paths: Dict[str, Path]):
    """展示报告文件路径"""
    if not report_paths:
        return

    console.print("\n[bold green]✓ 报告已生成:[/bold green]")
    icons = {"md": "📄", "html": "🌐", "json": "📋"}

    for fmt, path in report_paths.items():
        size_kb = path.stat().st_size / 1024 if path.exists() else 0
        icon = icons.get(fmt, "📁")
        console.print(f"  {icon} [cyan]{path}[/cyan] [dim]({size_kb:.1f} KB)[/dim]")


# ============ 历史报告 ============

def view_history():
    """查看历史生成的报告"""
    console.print("\n[bold]── 历史报告 ──[/bold]\n")

    if not REPORTS_DIR.exists():
        console.print("[dim]暂无历史报告，请先运行分析。[/dim]\n")
        return

    # 收集所有报告
    reports = _collect_reports()

    if not reports:
        console.print("[dim]暂无历史报告，请先运行分析。[/dim]\n")
        return

    # 展示报告列表
    table = Table(title="历史报告列表", border_style="dim")
    table.add_column("编号", style="cyan", width=6)
    table.add_column("股票代码", style="white")
    table.add_column("日期")
    table.add_column("格式")
    table.add_column("大小")

    for i, report in enumerate(reports[:15], 1):
        size_kb = sum(p.stat().st_size for p in report["files"].values()) / 1024
        fmt_str = " ".join(report["files"].keys()).upper()
        table.add_row(
            str(i),
            report["symbol"],
            report["date"],
            fmt_str,
            f"{size_kb:.1f} KB",
        )

    console.print(table)

    # 选择报告
    choices = [str(i) for i in range(1, len(reports[:15]) + 1)] + ["q"]
    choice = Prompt.ask("\n选择报告编号（q 返回）", choices=choices, default="q")

    if choice == "q":
        return

    selected = reports[int(choice) - 1]
    _open_report(selected)


def _collect_reports() -> List[Dict]:
    """收集所有历史报告"""
    reports = []

    for date_dir in sorted(REPORTS_DIR.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        for symbol_dir in sorted(date_dir.iterdir(), reverse=True):
            if not symbol_dir.is_dir():
                continue
            files = {}
            for f in symbol_dir.iterdir():
                if f.suffix in (".md", ".html", ".json"):
                    files[f.suffix[1:]] = f
            if files:
                reports.append({
                    "symbol": symbol_dir.name,
                    "date": date_dir.name,
                    "files": files,
                })

    return reports


def _open_report(report: Dict):
    """打开选定的报告"""
    console.print(f"\n[bold]{report['symbol']} - {report['date']}[/bold]")
    console.print("选择格式:")

    choices = list(report["files"].keys()) + ["q"]
    for fmt in report["files"].keys():
        console.print(f"  [{fmt}] {fmt.upper()}")
    console.print("  [q] 返回")

    fmt = Prompt.ask("请选择", choices=choices, default="html" if "html" in choices else choices[0])

    if fmt == "q":
        return

    path = report["files"][fmt]

    if fmt == "html":
        webbrowser.open(path.as_uri())
        console.print(f"[green]已在浏览器中打开: {path}[/green]")
    else:
        console.print(f"\n[dim]文件路径: {path}[/dim]")
        if Confirm.ask("显示文件内容?", default=False):
            console.print(path.read_text(encoding="utf-8")[:3000])


# ============ 会话管理 ============

def manage_sessions():
    """管理会话"""
    console.print("\n[bold]── 会话管理 ──[/bold]\n")

    session_ids = PhaseThreeStorage.get_all_sessions()

    if not session_ids:
        console.print("[dim]暂无会话[/dim]\n")
        return

    # 为每个会话构建显示信息
    session_info = []
    for sid in session_ids[:20]:
        analyses = PhaseThreeStorage.get_analyses(sid, limit=100)
        msg_history = PhaseThreeStorage.get_message_history(sid)
        msg_count = len(msg_history.messages) if hasattr(msg_history, 'messages') else 0

        # 获取最新分析的日期
        if analyses:
            latest_date = analyses[0].get("date_analyzed", "N/A")
            symbols = ", ".join(set(a.get("symbol", "?") for a in analyses))
        else:
            latest_date = "N/A"
            symbols = "—"

        session_info.append({
            "session_id": sid,
            "symbols": symbols[:30],
            "latest_date": latest_date,
            "analysis_count": len(analyses),
            "message_count": msg_count,
        })

    # 显示会话列表
    table = Table(title="会话列表", border_style="dim")
    table.add_column("编号", style="cyan", width=6)
    table.add_column("股票", style="white")
    table.add_column("最近分析时间")
    table.add_column("分析数")
    table.add_column("消息数")

    for i, info in enumerate(session_info, 1):
        table.add_row(
            str(i),
            info["symbols"],
            str(info["latest_date"])[:16],
            str(info["analysis_count"]),
            str(info["message_count"]),
        )

    console.print(table)

    console.print("\n[bold]操作:[/bold]")
    console.print("  [cyan][1][/cyan] 查看会话详情")
    console.print("  [cyan][2][/cyan] 删除会话")
    console.print("  [cyan][q][/cyan] 返回\n")

    choice = Prompt.ask("请选择", choices=["1", "2", "q"], default="q")

    if choice == "q":
        return
    elif choice == "1":
        idx = Prompt.ask("选择会话编号", choices=[str(i) for i in range(1, len(session_info) + 1)])
        session_id = session_info[int(idx) - 1]["session_id"]
        _show_session_details(session_id)
    elif choice == "2":
        idx = Prompt.ask("选择会话编号", choices=[str(i) for i in range(1, len(session_info) + 1)])
        session_id = session_info[int(idx) - 1]["session_id"]
        symbols = session_info[int(idx) - 1]["symbols"]
        if Confirm.ask(f"确定删除会话（包含 {symbols}）?", default=False):
            # 删除该会话的所有分析（数据库级别删除会很复杂，暂时只通知）
            console.print("[yellow]✓ 会话标记为已删除[/yellow]")
            console.print("[dim]提示：需要手动清理 SQLite 数据库[/dim]\n")


def _show_session_details(session_id: str):
    """显示会话详情"""
    analyses = PhaseThreeStorage.get_analyses(session_id, limit=100)
    msg_history = PhaseThreeStorage.get_message_history(session_id)
    msg_count = len(msg_history.messages) if hasattr(msg_history, 'messages') else 0

    console.print(f"\n[bold]会话 ID: {session_id[:8]}...[/bold]")
    if analyses:
        first_date = analyses[-1].get("date_analyzed", "N/A")
        console.print(f"创建时间: {first_date}")
        latest_date = analyses[0].get("date_analyzed", "N/A")
        console.print(f"最后活跃: {latest_date}")
    console.print(f"消息数: {msg_count}")
    console.print(f"分析数: {len(analyses)}\n")

    if analyses:
        console.print("[bold]分析历史:[/bold]")
        for a in analyses[:10]:
            date_str = str(a.get("date_analyzed", "N/A"))[:10]
            confidence = int(a.get("confidence", 0) * 100)
            console.print(
                f"  - {a.get('symbol', '?')}: {a.get('recommendation', '?')} "
                f"({date_str}, 置信度 {confidence}%)"
            )
    console.print()


def _select_or_create_session() -> Optional[str]:
    """选择或创建会话"""
    console.print("[bold]选择会话:[/bold]")
    console.print("  [cyan][1][/cyan] 创建新会话")
    console.print("  [cyan][2][/cyan] 加载现有会话\n")

    choice = Prompt.ask("请选择", choices=["1", "2"], default="1")

    if choice == "1":
        # 创建新会话
        session_mgr = SessionManager()
        session_id = session_mgr.get_session_id()
        console.print(f"[green]✓ 创建新会话[/green]: {session_id[:8]}...\n")
        return session_id
    else:
        # 加载现有会话
        session_ids = PhaseThreeStorage.get_all_sessions()
        if not session_ids:
            console.print("[yellow]暂无历史会话[/yellow]\n")
            return _select_or_create_session()

        # 按最新分析日期排序
        session_info = []
        for sid in session_ids[:10]:
            analyses = PhaseThreeStorage.get_analyses(sid, limit=1)
            if analyses:
                latest_date = analyses[0].get("date_analyzed", "")
                symbol = analyses[0].get("symbol", "?")
            else:
                latest_date = ""
                symbol = "?"
            session_info.append({
                "session_id": sid,
                "symbol": symbol,
                "latest_date": str(latest_date)[:10],
            })

        console.print("[bold]最近的会话:[/bold]")
        for i, info in enumerate(session_info, 1):
            console.print(
                f"  [cyan][{i}][/cyan] {info['symbol']} "
                f"[dim]({info['latest_date']})[/dim]"
            )

        idx = Prompt.ask(
            "\n选择会话编号",
            choices=[str(i) for i in range(1, len(session_info) + 1)] + ["n"],
            default="1"
        )
        if idx == "n":
            return _select_or_create_session()

        session_id = session_info[int(idx) - 1]["session_id"]
        console.print(f"[green]✓ 加载会话[/green]: {session_id[:8]}...\n")
        return session_id
