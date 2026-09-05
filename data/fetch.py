"""
Lấy dữ liệu giá thô (OHLCV) từ sàn hoặc file lịch sử.

Chỉ chịu trách nhiệm lấy dữ liệu — không làm sạch, không tính chỉ báo.
Việc đó thuộc về `data/pipeline.py`.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Candle:
    timestamp: int  # epoch seconds
    open: float
    high: float
    low: float
    close: float
    volume: float


def fetch_historical(symbol: str, timeframe: str, lookback_bars: int) -> List[Candle]:
    """
    Lấy `lookback_bars` nến gần nhất cho `symbol` ở khung `timeframe`.

    TODO: implement kết nối tới sàn thật (ccxt, binance API...) hoặc đọc từ CSV.
    Hiện tại raise NotImplementedError để tránh chạy nhầm với dữ liệu giả.
    """
    raise NotImplementedError("Cắm nguồn dữ liệu thật vào đây (API sàn hoặc CSV lịch sử).")


def fetch_latest_candle(symbol: str, timeframe: str) -> Candle:
    """Lấy nến mới nhất — dùng cho vòng lặp live, không dùng trong backtest."""
    raise NotImplementedError("Cắm nguồn dữ liệu real-time vào đây.")
