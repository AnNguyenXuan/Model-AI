"""
Lớp risk ở giai đoạn hiện tại CHỈ xử lý tín hiệu — CHƯA tính size, CHƯA đặt
SL/TP (đúng yêu cầu: "chưa cần yếu tố SL, chỉ cần tín hiệu trước").

Trách nhiệm duy nhất: khi decision engine phát hiện một ĐIỂM ĐẢO CHIỀU
(Signal.is_reversal=True), ghi log thông báo — dùng đúng timestamp của
NẾN tại thời điểm đó (không dùng giờ hệ thống), để log luôn khớp với thời
điểm tín hiệu thật sự xuất hiện trên chart kể cả khi chạy backtest trên dữ
liệu quá khứ.

Khi cần lại size/SL/TP (xem docs/roadmap.md giai đoạn 2), bổ sung lại vào
đây và vào risk/position_sizing.py — không cần đổi decision/ hay backtest/.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decision.base import Signal, Action

VN_TZ = timezone(timedelta(hours=7)) 

@dataclass
class Order:
    action: Action
    reason: str
    is_reversal: bool = False


class RiskManager:
    def __init__(self, log_path: str = "logs/reversals.log"):
        # logging.getLogger(name) trả về CÙNG 1 object cho cùng 1 tên trong
        # toàn bộ process — nếu dùng tên cố định "risk_manager", 2
        # RiskManager với log_path khác nhau (vd trong test) sẽ dính chung
        # handler cũ, ghi nhầm file. Dùng tên gắn với log_path + id(self)
        # để mỗi instance có logger/handler độc lập.
        self.logger = logging.getLogger(f"risk_manager.{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        # encoding="utf-8" bắt buộc để ghi đúng tiếng Việt có dấu trên mọi
        # hệ điều hành (xem execution/logger_execution.py để biết lý do
        # chi tiết).
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def build_order(self, signal: Signal, timestamp: int) -> Order:
        """
        `timestamp`: epoch giây (UTC) của nến đang xét trong vòng lặp
        backtest/live (candle.timestamp) — KHÔNG dùng datetime.now().
        """
        if signal.is_reversal:
            candle_time = datetime.fromtimestamp(timestamp, tz=VN_TZ).isoformat()
            self.logger.info(
                "[%s] Đảo chiều -> %s | %s",
                candle_time, signal.action.value.upper(), signal.reason,
            )

        return Order(action=signal.action, reason=signal.reason, is_reversal=signal.is_reversal)
