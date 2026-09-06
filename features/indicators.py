"""
Tính các chỉ báo kỹ thuật từ danh sách nến đã làm sạch.

Mỗi hàm chỉ dùng dữ liệu tại và trước thời điểm hiện tại — không bao giờ
nhìn về phía trước (tránh lookahead bias khi backtest).
"""

from typing import List, Optional, Tuple
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
    """
    RSI chuẩn Wilder.

    Bước 1: Change[i] = close[i] - close[i-1]; Gain = max(Change, 0),
            Loss = max(-Change, 0).
    Bước 2: Average Gain/Loss đầu tiên = trung bình cộng đơn giản của
            `period` giá trị Gain/Loss đầu tiên (cần period+1 nến đầu tiên
            để có đủ `period` giá trị Change).
    Bước 3: Từ đó về sau, làm mượt kiểu Wilder:
            AvgGain[i] = (AvgGain[i-1]*(period-1) + Gain[i]) / period
            AvgLoss[i] = (AvgLoss[i-1]*(period-1) + Loss[i]) / period
    Bước 4: RS = AvgGain/AvgLoss; RSI = 100 - 100/(1+RS).
            Nếu AvgLoss = 0 -> RSI = 100.

    Giá trị = None cho tới khi đủ dữ liệu (đồng bộ với `ema`/`atr` — mọi nơi
    đọc chỉ báo trong pipeline (decision/, backtest/engine.py) đều phải
    chấp nhận None cho các nến đầu).

    Muốn có "RSI ngắn" phản ứng nhanh hơn cho khung giờ biến động nhanh
    (xem chiến lược bắt sóng ngắn theo xu hướng vi mô), gọi rsi(candles, 7)
    hoặc rsi(candles, 9) thay vì mặc định 14.
    """
    n = len(candles)
    result: List[Optional[float]] = [None] * n
    if n <= period:
        return result

    closes = [c.close for c in candles]
    gains = [0.0] * (n - 1)
    losses = [0.0] * (n - 1)
    for i in range(1, n):
        change = closes[i] - closes[i - 1]
        gains[i - 1] = max(change, 0.0)
        losses[i - 1] = max(-change, 0.0)

    def _rsi_from_avg(avg_gain: float, avg_loss: float) -> float:
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result[period] = _rsi_from_avg(avg_gain, avg_loss)

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        result[i + 1] = _rsi_from_avg(avg_gain, avg_loss)

    return result


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


def macd(
    candles: List[Candle], fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    MACD = EMA(fast) - EMA(slow). Signal = EMA(signal) của đường MACD.
    Histogram = MACD - Signal.

    Dùng cho bước "xác nhận lực đẩy" (Lớp 3) trong chiến lược bắt sóng ngắn
    theo xu hướng vi mô: histogram đổi dấu đúng hướng xu hướng tại vùng giá
    hồi về EMA9/21 là tín hiệu xác nhận tốt để vào lệnh.

    Với khung giờ biến động nhanh, có thể rút ngắn tham số, ví dụ
    macd(candles, fast=5, slow=13, signal=6) thay vì bộ mặc định 12/26/9.

    Trả về 3 List cùng độ dài với `candles`, giá trị None cho tới khi đủ
    dữ liệu để tính (giống các hàm chỉ báo khác trong module này).
    """
    n = len(candles)
    ema_fast_series = ema(candles, fast)
    ema_slow_series = ema(candles, slow)

    macd_line: List[Optional[float]] = [None] * n
    for i in range(n):
        if ema_fast_series[i] is not None and ema_slow_series[i] is not None:
            macd_line[i] = ema_fast_series[i] - ema_slow_series[i]

    valid_indices = [i for i in range(n) if macd_line[i] is not None]
    signal_line: List[Optional[float]] = [None] * n
    histogram: List[Optional[float]] = [None] * n

    if len(valid_indices) >= signal:
        k = 2 / (signal + 1)
        seed_values = [macd_line[valid_indices[j]] for j in range(signal)]
        seed = sum(seed_values) / signal
        seed_idx = valid_indices[signal - 1]
        signal_line[seed_idx] = seed
        prev = seed
        for j in range(signal, len(valid_indices)):
            idx = valid_indices[j]
            prev = macd_line[idx] * k + prev * (1 - k)
            signal_line[idx] = prev

    for i in range(n):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram[i] = macd_line[i] - signal_line[i]

    return macd_line, signal_line, histogram
