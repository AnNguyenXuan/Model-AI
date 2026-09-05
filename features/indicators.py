"""
Tính các chỉ báo kỹ thuật từ danh sách nến đã làm sạch.

Mỗi hàm chỉ dùng dữ liệu tại và trước thời điểm hiện tại — không bao giờ
nhìn về phía trước (tránh lookahead bias khi backtest).
"""

from typing import List, Optional
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


def _true_range(candle: Candle, prev_close: Optional[float]) -> float:
    """
    True Range tại một nến:
    TR = max(high-low, |high-prev_close|, |low-prev_close|)
    Nếu không có nến trước (nến đầu tiên), TR = high - low.
    """
    if prev_close is None:
        return candle.high - candle.low
    return max(
        candle.high - candle.low,
        abs(candle.high - prev_close),
        abs(candle.low - prev_close),
    )


def atr(candles: List[Candle], period: int = 14) -> List[float]:
    """
    Average True Range — công thức Wilder.

    Bước 1: tính True Range (TR) cho từng nến, dùng close của nến TRƯỚC ĐÓ
            (không nhìn tương lai — an toàn cho backtest).
    Bước 2: ATR đầu tiên (tại index period-1) = trung bình cộng của `period`
            giá trị TR đầu tiên.
    Bước 3: từ đó về sau, làm mượt kiểu Wilder:
            ATR[i] = (ATR[i-1] * (period - 1) + TR[i]) / period

    Giá trị = None cho tới khi đủ dữ liệu (giống `ema`), để đồng bộ cách
    xử lý "chưa đủ dữ liệu" trên toàn bộ pipeline (xem decision/rule_based.py
    và backtest/engine.py — chỗ nào đọc chỉ báo đều phải chấp nhận None).
    """
    n = len(candles)
    result: List[Optional[float]] = [None] * n
    if n < period:
        return result

    true_ranges = [
        _true_range(candles[i], candles[i - 1].close if i > 0 else None)
        for i in range(n)
    ]

    first_atr = sum(true_ranges[:period]) / period
    result[period - 1] = first_atr

    for i in range(period, n):
        result[i] = (result[i - 1] * (period - 1) + true_ranges[i]) / period

    return result