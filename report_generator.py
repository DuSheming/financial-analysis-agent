"""
报告生成模块

生成 Markdown、HTML、JSON 格式的金融分析报告，含 matplotlib 图表
"""

import json
import base64
from datetime import datetime
from pathlib import Path
from io import BytesIO
from typing import Dict, Optional, Any
import logging

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from jinja2 import Template

from state import FinancialAnalysisState

logger = logging.getLogger(__name__)

# 配置 matplotlib - 支持中文
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Windows 系统：使用 SimHei 或 Microsoft YaHei (Windows 内置)
# macOS 系统：使用 SimHei, PingFang SC
# Linux 系统：使用 DejaVu Sans
import platform
import os

system = platform.system()

# 尝试显式注册和配置中文字体
_font_path = None
_font_prop = None

if system == "Windows":
    # 尝试找到SimHei字体文件
    font_candidates = [
        r'C:\Windows\Fonts\simhei.ttf',
        r'C:\Windows\Fonts\simyou.ttf',
        r'C:\Windows\Fonts\msyh.ttc',  # Microsoft YaHei
    ]
    for font_file in font_candidates:
        if os.path.exists(font_file):
            _font_path = font_file
            break

    if _font_path:
        # 显式注册字体到 matplotlib 字体管理器
        try:
            fm.fontManager.addfont(_font_path)
            _font_prop = fm.FontProperties(fname=_font_path)
            # 确保字体名称被 rcParams 使用
            registered_name = fm.FontProperties(fname=_font_path).get_name()
            available_fonts = [registered_name, 'SimHei', 'SimSun', 'Microsoft YaHei', 'DejaVu Sans']
            logger.info(f"Registered font: {_font_path}, name: {registered_name}")
        except Exception as e:
            logger.warning(f"Failed to register font {_font_path}: {e}")
            available_fonts = ['SimHei', 'SimSun', 'Microsoft YaHei', 'DejaVu Sans']
    else:
        available_fonts = ['SimHei', 'SimSun', 'Microsoft YaHei', 'DejaVu Sans']
elif system == "Darwin":  # macOS
    available_fonts = ['SimHei', 'PingFang SC', 'DejaVu Sans']
else:  # Linux
    available_fonts = ['SimHei', 'DejaVu Sans']

matplotlib.rcParams['font.sans-serif'] = available_fonts
matplotlib.rcParams['axes.unicode_minus'] = False  # 负号显示
plt.rcParams['figure.dpi'] = 100
plt.rcParams['font.size'] = 10
plt.rcParams['lines.linewidth'] = 1.5
try:
    plt.style.use('seaborn-v0_8-darkgrid')
except:
    plt.style.use('default')


# ============ 数据提取 ============

def _extract_data(state: FinancialAnalysisState) -> Dict[str, Any]:
    """从 state 中提取必要数据，返回新字典（不修改 state）"""
    try:
        hist_df = pd.read_json(state.get("historical_data", "[]"))
    except:
        hist_df = pd.DataFrame()

    return {
        "symbol": state.get("symbol", "UNKNOWN"),
        "timestamp": datetime.now().isoformat(),
        "historical_data": hist_df,
        "technical": state.get("technical_report", {}),
        "fundamental": state.get("fundamental_report", {}),
        "review": state.get("reviewer_summary", {}),
        "decision": state.get("final_recommendation", {}),
        "errors": state.get("errors", []),
        "data_quality": state.get("data_quality", {}),
    }


# ============ 图表生成 ============

def _generate_price_chart(df: pd.DataFrame, symbol: str) -> Optional[bytes]:
    """生成价格与移动平均线图表，返回 PNG 字节流"""
    if df.empty or "close" not in df.columns:
        return None

    try:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), gridspec_kw={'height_ratios': [3, 1]})

        # 确保日期列
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        else:
            df["date"] = range(len(df))

        # 价格 K 线
        ax1.plot(df["date"], df["close"], label="Close", color="black", linewidth=2)

        # 移动平均线
        for period, color in [(20, "blue"), (60, "orange"), (120, "red")]:
            if len(df) >= period:
                ma = df["close"].rolling(window=period).mean()
                ax1.plot(df["date"], ma, label=f"MA{period}", color=color, alpha=0.7)

        ax1.set_ylabel("Price ($)")
        ax1.legend(loc="upper left")
        ax1.set_title(f"{symbol} 价格走势与移动平均线", fontproperties=_font_prop if _font_prop else None)
        ax1.grid(True, alpha=0.3)

        # 成交量
        if "volume" in df.columns:
            ax2.bar(df["date"], df["volume"], color="gray", alpha=0.5, label="Volume")
            ax2.set_ylabel("Volume")
            ax2.legend(loc="upper left")

        ax2.set_xlabel("Date")

        # 格式化日期
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, len(df)//10)))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")

        plt.tight_layout()

        # 转换为 PNG 字节
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()
    except Exception as e:
        logger.error(f"Error generating price chart: {e}")
        return None


def _generate_indicators_chart(tech_report: Dict) -> Optional[bytes]:
    """生成技术指标图表（RSI + MACD）"""
    if not tech_report or "raw_indicators" not in tech_report:
        return None

    try:
        indicators = tech_report["raw_indicators"]

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))

        # RSI
        rsi = indicators.get("rsi", {})
        if rsi.get("success"):
            ax1.text(0.5, 0.7, f"RSI({rsi.get('period', 14)})",
                    ha="center", va="center", fontsize=12, fontweight="bold")
            ax1.text(0.5, 0.4, f"{rsi.get('value', 'N/A')}",
                    ha="center", va="center", fontsize=24, color="blue")
            ax1.text(0.5, 0.1, f"{rsi.get('signal', 'N/A')}",
                    ha="center", va="center", fontsize=10, color="gray")
            ax1.set_xlim(0, 1)
            ax1.set_ylim(0, 1)
            ax1.axis("off")

        # MACD
        macd = indicators.get("macd", {})
        if macd.get("success"):
            ax2.text(0.5, 0.8, "MACD", ha="center", fontsize=12, fontweight="bold")
            ax2.text(0.1, 0.6, f"MACD: {macd.get('macd', 'N/A'):.4f}", fontsize=9)
            ax2.text(0.1, 0.45, f"Signal: {macd.get('signal', 'N/A'):.4f}", fontsize=9)
            ax2.text(0.1, 0.3, f"Hist: {macd.get('histogram', 'N/A'):.4f}", fontsize=9)
            ax2.text(0.1, 0.15, f"Trend: {macd.get('interpretation', 'N/A')}", fontsize=9)
            ax2.set_xlim(0, 1)
            ax2.set_ylim(0, 1)
            ax2.axis("off")

        # 移动平均线
        ma = indicators.get("moving_averages", {})
        if ma.get("success"):
            values = ma.get("values", {})
            ax3.text(0.5, 0.85, "Moving Averages", ha="center", fontsize=11, fontweight="bold")
            y_pos = 0.7
            for label, value in list(values.items())[:4]:
                ax3.text(0.1, y_pos, f"{label}: {value}", fontsize=9, family="monospace")
                y_pos -= 0.15
            ax3.text(0.5, 0.05, f"Trend: {ma.get('trend', 'N/A')}",
                    ha="center", fontsize=9, color="blue", fontweight="bold")
            ax3.set_xlim(0, 1)
            ax3.set_ylim(0, 1)
            ax3.axis("off")

        # Bollinger Bands
        bb = indicators.get("bollinger_bands", {})
        if bb.get("success"):
            ax4.text(0.5, 0.8, "Bollinger Bands", ha="center", fontsize=11, fontweight="bold")
            ax4.text(0.1, 0.65, f"Upper: {bb.get('upper', 'N/A')}", fontsize=9)
            ax4.text(0.1, 0.5, f"Middle: {bb.get('middle', 'N/A')}", fontsize=9)
            ax4.text(0.1, 0.35, f"Lower: {bb.get('lower', 'N/A')}", fontsize=9)
            ax4.text(0.1, 0.2, f"Price: {bb.get('current_price', 'N/A')}", fontsize=9)
            ax4.text(0.1, 0.05, f"Position: {bb.get('position', 'N/A')}", fontsize=8, color="red")
            ax4.set_xlim(0, 1)
            ax4.set_ylim(0, 1)
            ax4.axis("off")

        plt.suptitle("技术指标详解", fontsize=14, fontweight="bold", fontproperties=_font_prop if _font_prop else None)
        plt.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()
    except Exception as e:
        logger.error(f"Error generating indicators chart: {e}")
        return None


# ============ 报告渲染 ============

MARKDOWN_TEMPLATE = """# {symbol} 金融分析报告

**生成时间**: {timestamp}

## 📊 执行摘要

| 指标 | 数值 |
|------|------|
| 最终推荐 | **{recommendation}** |
| 置信度 | {confidence}% |
| 目标价格 | ${target_price} |
| 止损价 | ${stop_loss} |
| 持仓建议 | {position_size} |

---

## 📈 技术分析

### 指标总览
- **趋势**: {technical_trend}
- **强度**: {technical_strength}
- **短期信号**: {technical_signal}

### 关键观察
{technical_observations}

### 技术面结论
{technical_summary}

---

## 💰 基本面分析

### 估值评估
- **估值水平**: {valuation_assessment}
- **增长潜力**: {growth_potential}
- **市场情绪**: {news_sentiment}

### 基本面结论
{fundamental_summary}

---

## 🔍 综合评审

### 共识水平
- **技术面与基本面**: {consensus_level}
- **整体情绪**: {overall_sentiment}
- **信心水平**: {reviewer_confidence}%

{contradictions_section}

---

## ✅ 投资建议

### 核心建议
```
推荐操作: {recommendation}
推荐理由: {recommendation_rationale}

入场策略:
  - 目标价格: ${target_price}
  - 止损价: ${stop_loss}
  - 建议仓位: {position_size}
  - 持有周期: {holding_period}
```

### 风险提示
{risks_section}

### 机会识别
{opportunities_section}

---

## 📋 数据质量

- 价格数据: {has_price_data}
- 基本面数据: {has_fundamentals}
- 新闻数据: {has_news}
- 总体评分: {quality_score}

---

**免责声明**: 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。

生成于 {timestamp} by AI 金融分析系统
"""


def render_markdown(data: Dict) -> str:
    """渲染 Markdown 报告"""
    decision = data["decision"]
    technical = data["technical"]
    fundamental = data["fundamental"]
    review = data["review"]
    quality = data["data_quality"]

    # 准备数据
    template_data = {
        "symbol": data["symbol"],
        "timestamp": data["timestamp"],
        "recommendation": decision.get("recommendation", "N/A"),
        "confidence": int(decision.get("confidence", 0) * 100),
        "target_price": decision.get("target_price", "N/A"),
        "stop_loss": decision.get("stop_loss", "N/A"),
        "position_size": decision.get("position_size", "正常"),
        "recommendation_rationale": decision.get("reasoning", "N/A"),
        "holding_period": decision.get("holding_period", "N/A"),

        "technical_trend": technical.get("trend", "N/A"),
        "technical_strength": technical.get("strength", "N/A"),
        "technical_signal": technical.get("short_term_signal", "N/A"),
        "technical_observations": "\n".join([f"- {obs}" for obs in technical.get("key_observations", [])[:3]]),
        "technical_summary": technical.get("summary", "N/A"),

        "valuation_assessment": fundamental.get("valuation_assessment", "N/A"),
        "growth_potential": fundamental.get("growth_potential", "N/A"),
        "news_sentiment": fundamental.get("news_sentiment", "N/A"),
        "fundamental_summary": fundamental.get("summary", "N/A"),

        "consensus_level": review.get("consensus_level", "N/A"),
        "overall_sentiment": review.get("overall_sentiment", "N/A"),
        "reviewer_confidence": int(review.get("confidence_level", 0) * 100),
        "contradictions_section": _format_contradictions(review),

        "risks_section": "\n".join([f"- {r}" for r in decision.get("risks", [])[:5]]),
        "opportunities_section": "\n".join([f"- {o}" for o in decision.get("opportunities", [])[:5]]),

        "has_price_data": "✓" if quality.get("has_price_data") else "✗",
        "has_fundamentals": "✓" if quality.get("has_fundamentals") else "✗",
        "has_news": "✓" if quality.get("has_news") else "✗",
        "quality_score": f"{quality.get('quality_score', 0):.0%}",
    }

    return MARKDOWN_TEMPLATE.format(**template_data)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} - 金融分析报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.1em; opacity: 0.9; }}

        .content {{ padding: 40px; }}

        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}

        .summary-table th,
        .summary-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}

        .summary-table th {{
            background-color: #f9f9f9;
            font-weight: bold;
        }}

        .summary-table tr:hover {{ background-color: #f5f5f5; }}

        .recommendation {{
            font-size: 1.5em;
            font-weight: bold;
        }}

        .buy {{ color: #00a000; }}
        .sell {{ color: #cc0000; }}
        .hold {{ color: #ff9800; }}

        .section {{
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-left: 4px solid #667eea;
        }}

        .section h2 {{ margin-bottom: 15px; color: #333; }}
        .section h3 {{ margin-top: 15px; margin-bottom: 10px; color: #555; }}

        .chart {{
            margin: 20px 0;
            text-align: center;
        }}

        .chart img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .risk-list, .opportunity-list {{
            list-style: none;
            padding-left: 20px;
        }}

        .risk-list li:before {{
            content: "⚠ ";
            color: #cc0000;
            font-weight: bold;
            margin-right: 10px;
        }}

        .opportunity-list li:before {{
            content: "🎯 ";
            margin-right: 10px;
        }}

        .footer {{
            background: #f0f0f0;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }}

        @media print {{
            body {{ background: white; }}
            .container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{symbol} 投资分析报告</h1>
            <p>生成时间: {timestamp}</p>
        </div>

        <div class="content">
            <section class="section">
                <h2>📊 执行摘要</h2>
                <table class="summary-table">
                    <tr>
                        <th>指标</th>
                        <th>数值</th>
                    </tr>
                    <tr>
                        <td>最终推荐</td>
                        <td class="recommendation {recommendation_class}">{recommendation}</td>
                    </tr>
                    <tr>
                        <td>置信度</td>
                        <td>{confidence}%</td>
                    </tr>
                    <tr>
                        <td>目标价格</td>
                        <td>${target_price}</td>
                    </tr>
                    <tr>
                        <td>止损价</td>
                        <td>${stop_loss}</td>
                    </tr>
                    <tr>
                        <td>建议仓位</td>
                        <td>{position_size}</td>
                    </tr>
                </table>
            </section>

            <section class="section">
                <h2>📈 技术分析</h2>
                <h3>指标总览</h3>
                <p><strong>趋势</strong>: {technical_trend}</p>
                <p><strong>强度</strong>: {technical_strength}</p>
                <p><strong>短期信号</strong>: {technical_signal}</p>
                <div class="chart">
                    <img src="data:image/png;base64,{chart_indicators}" alt="技术指标">
                </div>
                <p><strong>结论</strong>: {technical_summary}</p>
            </section>

            <section class="section">
                <h2>💰 基本面分析</h2>
                <p><strong>估值评估</strong>: {valuation_assessment}</p>
                <p><strong>增长潜力</strong>: {growth_potential}</p>
                <p><strong>市场情绪</strong>: {news_sentiment}</p>
                <p><strong>结论</strong>: {fundamental_summary}</p>
            </section>

            <section class="section">
                <h2>🔍 综合评审</h2>
                <p><strong>共识水平</strong>: {consensus_level}</p>
                <p><strong>整体情绪</strong>: {overall_sentiment}</p>
                <p><strong>信心水平</strong>: {reviewer_confidence}%</p>
            </section>

            <section class="section">
                <h2>⚡ 风险与机会</h2>
                <h3>主要风险</h3>
                <ul class="risk-list">
                    {risks_html}
                </ul>
                <h3>主要机会</h3>
                <ul class="opportunity-list">
                    {opportunities_html}
                </ul>
            </section>

            <section class="section">
                <h2>📋 数据质量</h2>
                <p>价格数据: {has_price_data} | 基本面数据: {has_fundamentals} | 新闻数据: {has_news}</p>
                <p>总体评分: {quality_score}</p>
            </section>
        </div>

        <div class="footer">
            <p>本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。</p>
            <p>由 AI 金融分析系统自动生成 | {timestamp}</p>
        </div>
    </div>
</body>
</html>
"""


def render_html(data: Dict, chart_bytes: Optional[bytes] = None) -> str:
    """渲染 HTML 报告"""
    decision = data["decision"]
    technical = data["technical"]
    fundamental = data["fundamental"]
    review = data["review"]
    quality = data["data_quality"]

    # 转换图表为 base64
    chart_b64 = ""
    if chart_bytes:
        chart_b64 = base64.b64encode(chart_bytes).decode("utf-8")

    # 决策颜色
    recommendation = decision.get("recommendation", "HOLD")
    rec_class = "buy" if "买入" in recommendation or "买" in recommendation else \
                "sell" if "卖出" in recommendation or "卖" in recommendation else "hold"

    # 格式化风险和机会
    risks_html = "\n".join([f"<li>{r}</li>" for r in decision.get("risks", [])[:5]])
    opportunities_html = "\n".join([f"<li>{o}</li>" for o in decision.get("opportunities", [])[:5]])

    template_data = {
        "symbol": data["symbol"],
        "timestamp": data["timestamp"],
        "recommendation": recommendation,
        "recommendation_class": rec_class,
        "confidence": int(decision.get("confidence", 0) * 100),
        "target_price": decision.get("target_price", "N/A"),
        "stop_loss": decision.get("stop_loss", "N/A"),
        "position_size": decision.get("position_size", "N/A"),

        "technical_trend": technical.get("trend", "N/A"),
        "technical_strength": technical.get("strength", "N/A"),
        "technical_signal": technical.get("short_term_signal", "N/A"),
        "technical_summary": technical.get("summary", "N/A"),

        "valuation_assessment": fundamental.get("valuation_assessment", "N/A"),
        "growth_potential": fundamental.get("growth_potential", "N/A"),
        "news_sentiment": fundamental.get("news_sentiment", "N/A"),
        "fundamental_summary": fundamental.get("summary", "N/A"),

        "consensus_level": review.get("consensus_level", "N/A"),
        "overall_sentiment": review.get("overall_sentiment", "N/A"),
        "reviewer_confidence": int(review.get("confidence_level", 0) * 100),

        "chart_indicators": chart_b64,
        "risks_html": risks_html,
        "opportunities_html": opportunities_html,

        "has_price_data": "✓" if quality.get("has_price_data") else "✗",
        "has_fundamentals": "✓" if quality.get("has_fundamentals") else "✗",
        "has_news": "✓" if quality.get("has_news") else "✗",
        "quality_score": f"{quality.get('quality_score', 0):.0%}",
    }

    return HTML_TEMPLATE.format(**template_data)


def _format_contradictions(review: Dict) -> str:
    """格式化矛盾点"""
    contradictions = review.get("contradictions", [])
    if not contradictions:
        return "### 无明显矛盾\n\n技术面与基本面评估一致，投资逻辑清晰。"

    text = "### 矛盾点分析\n\n"
    for c in contradictions[:3]:
        text += f"**{c.get('area', 'N/A')}**\n"
        text += f"- 技术面: {c.get('technical_view', 'N/A')}\n"
        text += f"- 基本面: {c.get('fundamental_view', 'N/A')}\n"
        text += f"- 解释: {c.get('resolution', 'N/A')}\n\n"

    return text


# ============ 导出 ============

def export_report(
    state: FinancialAnalysisState,
    formats: list = None,
    output_dir: Path = None,
) -> Dict[str, Path]:
    """
    导出报告到文件

    Args:
        state: FinancialAnalysisState
        formats: ['md', 'html', 'json'] 等，默认全部
        output_dir: 输出目录，默认 ./reports (转换为绝对路径)

    Returns:
        {format: Path} 字典，如 {'md': Path(...), 'html': Path(...)}
    """
    if formats is None:
        formats = ["md", "html", "json"]

    if output_dir is None:
        output_dir = Path("./reports")

    # 转换为绝对路径（避免 as_uri() 错误）
    output_dir = output_dir.resolve()

    # 创建输出目录
    symbol = state.get("symbol", "UNKNOWN")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = output_dir / datetime.now().strftime("%Y-%m-%d") / symbol
    report_dir.mkdir(parents=True, exist_ok=True)

    # 提取数据
    data = _extract_data(state)

    result = {}

    # Markdown
    if "md" in formats:
        md_content = render_markdown(data)
        md_path = report_dir / f"report_{timestamp}.md"
        md_path.write_text(md_content, encoding="utf-8")
        result["md"] = md_path
        logger.info(f"Markdown report saved: {md_path}")

    # HTML（带图表）
    if "html" in formats:
        chart_bytes = _generate_indicators_chart(data["technical"])
        html_content = render_html(data, chart_bytes)
        html_path = report_dir / f"report_{timestamp}.html"
        html_path.write_text(html_content, encoding="utf-8")
        result["html"] = html_path
        logger.info(f"HTML report saved: {html_path}")

    # JSON
    if "json" in formats:
        json_content = {
            "symbol": symbol,
            "timestamp": data["timestamp"],
            "technical": data["technical"],
            "fundamental": data["fundamental"],
            "review": data["review"],
            "decision": data["decision"],
            "data_quality": data["data_quality"],
        }
        json_path = report_dir / f"report_{timestamp}.json"
        json_path.write_text(json.dumps(json_content, ensure_ascii=False, indent=2), encoding="utf-8")
        result["json"] = json_path
        logger.info(f"JSON report saved: {json_path}")

    return result
