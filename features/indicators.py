"""
Tính các chỉ báo kỹ thuật từ danh sách nến đã làm sạch.

Mỗi hàm chỉ dùng dữ liệu tại và trước thời điểm hiện tại — không bao giờ
nhìn về phía trước (tránh lookahead bias khi backtest).
"""

from typing import List
from data.fetch import Candle


def ema(candles: List[Candle], period: int) -> List[float]:
    """EMA chuẩn, giá trị đầu = None cho tới khi đủ dữ liệu."""
    closes = [c.close for c in candles]
    k = 2 / (period + 1)
    result = [None] * len(closes)
    if len(closes) < period:
        return result
    sma = sum(closes[:period]) / period
    result[period - 1] = sma
    for i in range(period, len(closes)):
        result[i] = closes[i] * k + result[i - 1] * (1 - k)
    return result


def rsi(candles: List[Candle], period: int = 14) -> List[float]:
    """RSI chuẩn Wilder. TODO: implement đầy đủ."""
    raise NotImplementedError("Cài đặt công thức RSI Wilder tại đây.")


def atr(candles: List[Candle], period: int = 14) -> List[float]:
    """Average True Range — dùng cho position sizing và stop-loss động."""
    raise NotImplementedError("Cài đặt công thức ATR (True Range trung bình) tại đây.")
