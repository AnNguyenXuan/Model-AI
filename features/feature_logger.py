"""
Ghi log giá trị các feature (EMA, RSI, ...) theo từng nến ra file — dùng để
đối chiếu thủ công với tính tay (xem docs/roadmap.md, giai đoạn 1: "kiểm
chứng bằng vài case tay"), hoặc để soi lại khi debug tín hiệu sai.

Đây chỉ là công cụ quan sát, KHÔNG nằm trong luồng chính (data -> features
-> decision -> risk -> execution) và không ảnh hưởng gì tới pipeline —
gọi rời sau khi có kết quả `build_features()`.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List

from data.fetch import Candle
from datetime import datetime, timezone, timedelta

VN_TZ = timezone(timedelta(hours=7))

def log_features(
    candles: List[Candle],
    features: Dict[str, list],
    log_path: str = "logs/features.log",
) -> None:
    """
    Ghi mỗi nến một dòng: thời gian UTC (dễ đọc, không phải epoch) + giá
    đóng cửa + giá trị TẤT CẢ feature có trong `features` tại đúng nến đó.

    `features[<tên>][i]` phải khớp `candles[i]` (đúng như quy ước trong
    backtest/engine.py) — hàm này không tự align lại, chỉ log theo đúng
    chỉ số i đã truyền vào.

    Vì dùng chung tên biến `features` (không hardcode ema_fast/rsi_fast),
    hàm log được mọi bộ indicator khai báo trong config.yaml — thêm/bớt
    indicator trong config thì log tự thêm/bớt cột theo, không cần sửa
    hàm này.

    Giá trị None (vài nến đầu chưa đủ dữ liệu cho EMA/RSI) được in là
    "None" thay vì làm lỗi định dạng %.4f.
    """
    # Logger riêng theo log_path + id(candles) để không dính chung handler
    # với lần gọi khác trong cùng process (giống lý do trong risk_manager.py).
    logger = logging.getLogger(f"feature_logger.{id(candles)}.{log_path}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    feature_names = list(features.keys())

    for i, candle in enumerate(candles):
        candle_time = datetime.fromtimestamp(candle.timestamp, tz=VN_TZ).isoformat()
        parts = [f"{name}={_fmt(features[name][i])}" for name in feature_names]
        logger.info("[%s] close=%.2f %s", candle_time, candle.close, " ".join(parts))

    handler.close()
    logger.removeHandler(handler)


def _fmt(value) -> str:
    return "None" if value is None else f"{value:.4f}"