"""
金融分析 Agent 系统入口

用法：
    python main.py                          # 交互式菜单
    python main.py "分析 600519.SH 长期"    # 直接分析（自动生成报告）
    python main.py 600519.SH               # 指定股票代码，使用默认设置
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.WARNING,            # 交互模式下只显示警告以上
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def _run_direct(request: str, session_id: str = None):
    """命令行直接分析模式（非交互）"""
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

    from state import FinancialAnalysisState
    from graph import build_graph
    from report_generator import export_report
    from storage import SessionManager, ContextManager

    console = Console()

    # 如果传入的是纯股票代码，构造完整请求
    if len(request.split()) == 1:
        request = f"分析股票 {request.upper()}，给出长期投资建议。股票代码是 {request.upper()}。"

    console.print(f"\n[bold cyan]开始分析: [/bold cyan]{request[:60]}")

    try:
        # 初始化或加载会话
        session_mgr = SessionManager(session_id)
        current_session_id = session_mgr.get_session_id()
        console.print(f"[dim]会话 ID: {current_session_id[:8]}...[/dim]\n")

        # 初始化上下文管理器
        ctx_mgr = ContextManager(current_session_id)

        app = build_graph()

        # 从请求中尝试提取股票代码作为显示
        initial_state = FinancialAnalysisState(
            initial_request=request,
            planned_tasks=[],
            symbol="",
            date_range=None,
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

        # 注入上下文（如果有之前的分析）
        initial_state = ctx_mgr.inject_context_into_state(initial_state)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("运行分析工作流...", total=None)
            final_state = app.invoke(initial_state)
            progress.update(task, description="分析完成 ✓")

        # 保存分析到数据库
        symbol = final_state.get("symbol", "UNKNOWN")
        date_range = final_state.get("date_range") or {}
        start_date = date_range.get("start", (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"))
        end_date = date_range.get("end", datetime.now().strftime("%Y-%m-%d"))

        session_mgr.save_analysis(symbol, final_state)
        ctx_mgr.add_message("ai", f"已分析 {symbol}，建议：{final_state.get('final_recommendation', {}).get('recommendation', 'N/A')}")

        # 输出摘要
        _print_summary(final_state, console)

        # 生成报告
        console.print("\n[bold]生成报告文件...[/bold]")
        report_paths = export_report(final_state, ["md", "html", "json"])

        console.print("\n[bold green]✓ 报告已生成:[/bold green]")
        for fmt, path in report_paths.items():
            size_kb = path.stat().st_size / 1024
            console.print(f"  {'📄' if fmt == 'md' else '🌐' if fmt == 'html' else '📋'} "
                          f"[cyan]{path}[/cyan] [dim]({size_kb:.1f} KB)[/dim]")

        # 自动打开 HTML
        if "html" in report_paths:
            import webbrowser
            from rich.prompt import Confirm
            if Confirm.ask("\n在浏览器中打开 HTML 报告?", default=True):
                webbrowser.open(report_paths["html"].as_uri())

    except Exception as e:
        console.print(f"\n[red]❌ 分析失败: {e}[/red]")
        logging.exception("Analysis failed")


def _print_summary(state, console):
    """在终端打印分析摘要"""
    from rich.table import Table

    rec = state.get("final_recommendation") or {}
    tech = state.get("technical_report") or {}
    fund = state.get("fundamental_report") or {}
    review = state.get("reviewer_summary") or {}
    symbol = state.get("symbol", "UNKNOWN")

    recommendation = rec.get("recommendation", "N/A")
    rec_color = "green" if "买" in recommendation else \
                "red" if "卖" in recommendation else "yellow"

    table = Table(title=f"{symbol} 分析结果", border_style="dim")
    table.add_column("维度", style="cyan", min_width=12)
    table.add_column("结果")

    table.add_row("最终建议", f"[bold {rec_color}]{recommendation}[/bold {rec_color}]")
    table.add_row("置信度", f"{int(rec.get('confidence', 0) * 100)}%")
    table.add_row("目标价格", str(rec.get("target_price", "N/A")))
    table.add_row("止损价", str(rec.get("stop_loss", "N/A")))
    table.add_row("持有周期", str(rec.get("holding_period", "N/A")))
    table.add_row("技术趋势", str(tech.get("trend", "N/A")))
    table.add_row("估值评估", str(fund.get("valuation_assessment", "N/A")))
    table.add_row("整体情绪", str(review.get("overall_sentiment", "N/A")))

    console.print()
    console.print(table)

    if rec.get("reasoning"):
        console.print(f"\n[bold]决策理由:[/bold] {rec.get('reasoning')[:200]}")

    errors = state.get("errors", [])
    if errors:
        console.print(f"\n[yellow]⚠ {len(errors)} 项警告:[/yellow]")
        for err in errors[:3]:
            console.print(f"  [dim]- {err}[/dim]")


def main():
    """
    智能入口：
    - 无参数   → 交互模式选择（菜单式 或 智能对话式）
    - 有参数   → 命令行直接分析
    """
    args = sys.argv[1:]

    if not args:
        # 交互模式 - 让用户选择
        from rich.console import Console
        from rich.prompt import Prompt

        console = Console()
        console.print(
            """
[bold cyan]╔═══════════════════════════════════╗
║  选择交互模式                     ║
╚═══════════════════════════════════╝[/bold cyan]

[bold][1][/bold] 📋 传统菜单式交互
   - 经典菜单选择
   - 逐步指引
   - 熟悉的操作方式

[bold][2][/bold] 💬 智能对话式交互 (推荐) ⭐ NEW
   - 自然语言对话
   - 多轮连续交互
   - 自动意图识别
   - LLM 智能决策
"""
        )

        choice = Prompt.ask(
            "[cyan]请选择[/cyan]", choices=["1", "2"], default="2"
        )

        if choice == "2":
            # 新的智能对话式交互
            from cli.smart_interactive import run_smart_interactive

            run_smart_interactive()
        else:
            # 原有的菜单式交互
            from cli.interactive import run_interactive

            run_interactive()
    else:
        # 命令行直接模式
        request = " ".join(args)
        _run_direct(request)


if __name__ == "__main__":
    main()
