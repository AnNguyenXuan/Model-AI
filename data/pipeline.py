"""
Làm sạch và chuẩn hoá dữ liệu thô trước khi đưa vào tính feature.

Trách nhiệm:
- Loại bỏ nến trùng/thiếu, kiểm tra gap thời gian.
- Đảm bảo dữ liệu được sắp xếp theo thời gian tăng dần (chống leak tương lai).
"""

from typing import List
from data.fetch import Candle


def clean_candles(candles: List[Candle]) -> List[Candle]:
    """
    Sắp xếp theo timestamp, loại bỏ trùng lặp, kiểm tra gap bất thường.

    QUAN TRỌNG cho backtest: hàm này không được phép nhìn thấy hoặc dùng dữ liệu
    ở thời điểm sau nến đang xét — mọi transform ở đây phải chỉ dùng dữ liệu
    quá khứ tương đối so với từng nến.
    """
    seen = {}
    for c in candles:
        seen[c.timestamp] = c  # loại trùng, giữ bản ghi cuối cùng
    ordered = sorted(seen.values(), key=lambda c: c.timestamp)
    return ordered


def validate_no_gaps(candles: List[Candle], expected_interval_sec: int) -> List[int]:
    """Trả về danh sách timestamp bị thiếu nến (gap) để cảnh báo, không tự động vá."""
    gaps = []
    for prev, cur in zip(candles, candles[1:]):
        if cur.timestamp - prev.timestamp != expected_interval_sec:
            gaps.append(cur.timestamp)
    return gaps
