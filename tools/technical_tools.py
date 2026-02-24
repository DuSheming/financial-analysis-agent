"""
技术指标计算工具

计算 RSI、MACD、移动平均线、布林带等指标。
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def parse_data_from_json(data_json: str):
    """从 JSON 字符串解析为 DataFrame"""
    try:
        import pandas as pd

        data = json.loads(data_json)
        df = pd.DataFrame(data)
        df.columns = [c.lower() for c in df.columns]

        # 标准化列名和数据类型
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df.dropna(subset=["close"])

    except Exception as e:
        logger.error(f"Error parsing data: {e}")
        raise


def calculate_rsi(data_json: str, period: int = 14) -> Dict[str, Any]:
    """
    计算相对强度指数 (RSI)

    RSI > 70: 超买
    RSI < 30: 超卖
    RSI 30-70: 中性

    Returns:
        {"success": bool, "value": float, "signal": str, "interpretation": str}
    """
    try:
        df = parse_data_from_json(data_json)

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta).where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        latest_rsi = float(rsi.iloc[-1])

        if latest_rsi > 70:
            signal = "overbought"
        elif latest_rsi < 30:
            signal = "oversold"
        else:
            signal = "neutral"

        return {
            "success": True,
            "indicator": "RSI",
            "period": period,
            "value": round(latest_rsi, 2),
            "signal": signal,
            "interpretation": f"RSI {latest_rsi:.1f} - {signal.upper()}",
        }

    except Exception as e:
        logger.error(f"RSI calculation error: {e}")
        return {"success": False, "error": str(e)}


def calculate_macd(
    data_json: str, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> Dict[str, Any]:
    """
    计算 MACD (Moving Average Convergence Divergence)

    Returns:
        {"success": bool, "macd": float, "signal": float, "histogram": float, "interpretation": str}
    """
    try:
        df = parse_data_from_json(data_json)

        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        latest_macd = float(macd_line.iloc[-1])
        latest_signal = float(signal_line.iloc[-1])
        latest_histogram = float(histogram.iloc[-1])

        # 判断信号（MACD 穿越 Signal 线）
        if latest_histogram > 0 and histogram.iloc[-2] <= 0:
            interp = "bullish_crossover"
        elif latest_histogram < 0 and histogram.iloc[-2] >= 0:
            interp = "bearish_crossover"
        elif latest_histogram > 0:
            interp = "bullish"
        else:
            interp = "bearish"

        return {
            "success": True,
            "indicator": "MACD",
            "macd": round(latest_macd, 4),
            "signal": round(latest_signal, 4),
            "histogram": round(latest_histogram, 4),
            "interpretation": interp,
        }

    except Exception as e:
        logger.error(f"MACD calculation error: {e}")
        return {"success": False, "error": str(e)}


def calculate_moving_averages(
    data_json: str, periods: List[int] = None
) -> Dict[str, Any]:
    """
    计算多条移动平均线 (MA)

    常用周期: [20, 60, 120, 250] (日线)

    Returns:
        {"success": bool, "values": {MA20: float, ...}, "trend": str}
    """
    if periods is None:
        periods = [20, 60, 120, 250]

    try:
        df = parse_data_from_json(data_json)

        mas = {}
        for period in periods:
            if period <= len(df):
                ma = df["close"].rolling(window=period).mean()
                mas[f"MA{period}"] = round(float(ma.iloc[-1]), 2)

        # 判断趋势
        if len(mas) >= 2:
            ma_vals = list(mas.values())
            # 均线多头排列 (MA20 > MA60 > MA120 > MA250) 表示上升趋势
            if all(ma_vals[i] >= ma_vals[i + 1] for i in range(len(ma_vals) - 1)):
                trend = "downtrend"
            elif all(ma_vals[i] <= ma_vals[i + 1] for i in range(len(ma_vals) - 1)):
                trend = "uptrend"
            else:
                trend = "consolidating"
        else:
            trend = "unknown"

        return {
            "success": True,
            "indicator": "Moving Averages",
            "values": mas,
            "trend": trend,
        }

    except Exception as e:
        logger.error(f"MA calculation error: {e}")
        return {"success": False, "error": str(e)}


def calculate_bollinger_bands(
    data_json: str, period: int = 20, std_dev: float = 2.0
) -> Dict[str, Any]:
    """
    计算布林带 (Bollinger Bands)

    Returns:
        {"success": bool, "upper": float, "middle": float, "lower": float, "position": str}
    """
    try:
        df = parse_data_from_json(data_json)

        sma = df["close"].rolling(window=period).mean()
        std = df["close"].rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        latest_close = float(df["close"].iloc[-1])
        latest_upper = float(upper.iloc[-1])
        latest_middle = float(sma.iloc[-1])
        latest_lower = float(lower.iloc[-1])

        if latest_close >= latest_upper:
            position = "at_upper_band"
        elif latest_close <= latest_lower:
            position = "at_lower_band"
        else:
            position = "within_bands"

        return {
            "success": True,
            "indicator": "Bollinger Bands",
            "upper": round(latest_upper, 2),
            "middle": round(latest_middle, 2),
            "lower": round(latest_lower, 2),
            "current_price": round(latest_close, 2),
            "position": position,
        }

    except Exception as e:
        logger.error(f"Bollinger Bands calculation error: {e}")
        return {"success": False, "error": str(e)}
