"""
Tính các chỉ báo kỹ thuật từ danh sách nến đã làm sạch.

Mỗi hàm chỉ dùng dữ liệu tại và trước thời điểm hiện tại — không bao giờ
nhìn về phía trước (tránh lookahead bias khi backtest).

Mọi hàm ở đây đều nhận tham số (period, fast/slow/signal...) thay vì cố
định cứng — không có "rsi_14()" hay "ema_20()" riêng, chỉ có rsi(candles,
period) / ema(candles, period) dùng chung cho mọi period cần thiết. Muốn
thêm chỉ báo mới: viết thêm 1 hàm nhận (candles, **params) rồi đăng ký vào
`features/registry.py` — không cần sửa file này cho những chỉ báo đã có.

LƯU Ý: đã bỏ `atr`/`_true_range` khỏi module này (xem yêu cầu: hiện tại
chưa cần yếu tố SL, chỉ cần tín hiệu trước). Khi nào cần lại ATR để tính
size/SL (risk/position_sizing.py), thêm lại hàm `atr` vào đây.
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

    Giá trị = None cho tới khi đủ dữ liệu (đồng bộ với `ema` — mọi nơi đọc
    chỉ báo trong pipeline (decision/, backtest/engine.py) đều phải chấp
    nhận None cho các nến đầu).

    Gọi với period khác nhau tuỳ nhu cầu, ví dụ rsi(candles, 9) cho chiến
    lược đảo chiều theo RSI ngắn, hoặc rsi(candles, 14) cho RSI chuẩn.
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


def macd(
    candles: List[Candle], fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    MACD = EMA(fast) - EMA(slow). Signal = EMA(signal) của đường MACD.
    Histogram = MACD - Signal.

    GIỮ LẠI như một hàm feature dùng chung (đúng yêu cầu: feature viết dạng
    hàm nhận tham số), nhưng KHÔNG còn được decision/trend_reversal.py sử
    dụng nữa — chiến lược MACD tạm thời bị loại bỏ theo yêu cầu. Muốn dùng
    lại: gọi macd(candles, fast=..., slow=..., signal=...) và đăng ký thêm
    field vào MarketState/config như trước.

    Trả về 3 List cùng độ dài với `candles`, giá trị None cho tới khi đủ
    dữ liệu để tính (giống các hàm chỉ báo khác trong module này).
    """
    ema_fast = ema(candles, fast)
    ema_slow = ema(candles, slow)

    macd_line: List[Optional[float]] = [None] * len(candles)
    for i in range(len(candles)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]

    first_valid = next((i for i, v in enumerate(macd_line) if v is not None), None)
    signal_line: List[Optional[float]] = [None] * len(candles)
    histogram: List[Optional[float]] = [None] * len(candles)

    if first_valid is not None:
        valid_macd = [v for v in macd_line[first_valid:] if v is not None]
        if len(valid_macd) >= signal:
            k = 2 / (signal + 1)
            sma = sum(valid_macd[:signal]) / signal
            idx = first_valid + signal - 1
            signal_line[idx] = sma
            for offset in range(signal, len(valid_macd)):
                idx = first_valid + offset
                signal_line[idx] = macd_line[idx] * k + signal_line[idx - 1] * (1 - k)

    for i in range(len(candles)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram[i] = macd_line[i] - signal_line[i]

    return macd_line, signal_line, histogram
