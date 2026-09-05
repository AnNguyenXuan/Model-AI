"""
Tính các nhãn phụ trợ cho risk management (không dùng để ra tín hiệu vào lệnh).

Ví dụ: mức độ biến động hiện tại, dùng để điều chỉnh position size.
"""

from typing import List
from data.fetch import Candle


def volatility_bucket(atr_values: List[float], lookback: int = 100) -> str:
    """
    Phân loại volatility hiện tại (thấp/trung bình/cao) dựa trên phân vị ATR
    trong `lookback` nến gần nhất. Dùng để risk_manager điều chỉnh size lệnh.
    """
    raise NotImplementedError("So sánh ATR hiện tại với phân vị lịch sử tại đây.")
