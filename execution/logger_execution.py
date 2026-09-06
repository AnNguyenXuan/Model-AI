"""
Execution layer PHIÊN BẢN CHỈ GHI LOG.

Theo yêu cầu: lớp execution hiện tại không kết nối sàn, chỉ ghi lại
lệnh sẽ được gửi (nếu có sàn thật) ra file/console, và trả về kết quả
khớp lệnh giả lập (fill tại giá đóng cửa nến hiện tại) để backtest engine
vẫn tính được PnL.

Khi cần kết nối sàn thật: tạo `execution/live_execution.py` implement
cùng method `send_order(order, fill_price) -> ExecutionResult`, và đổi
`execution.mode` trong config.yaml từ "log_only" sang "live" — không cần
sửa file này hay bất kỳ lớp nào khác.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from risk.risk_manager import Order
from decision.base import Action
from datetime import timezone, timedelta

VN_TZ = timezone(timedelta(hours=7))

@dataclass
class ExecutionResult:
    filled: bool
    fill_price: float
    order: Order


class LoggerExecution:
    def __init__(self, log_path: str = "logs/orders.log"):
        self.logger = logging.getLogger("execution")
        self.logger.setLevel(logging.INFO)
        # encoding="utf-8" là bắt buộc: mặc định trên Windows, FileHandler
        # dùng codepage của hệ thống (thường là cp1252), không encode được
        # tiếng Việt có dấu (ví dụ "cắt", "xuống") -> UnicodeEncodeError khi
        # ghi log. Ép utf-8 để log luôn ghi đúng bất kể chạy trên OS nào.
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        self.logger.addHandler(handler)

    def send_order(self, order: Order, current_price: float) -> ExecutionResult:
        if order.action == Action.HOLD:
            return ExecutionResult(filled=False, fill_price=0.0, order=order)

        self.logger.info(
            "%s | action=%s size=%.6f entry=%.2f sl=%.2f tp=%.2f reason=%s",
            datetime.now(VN_TZ).isoformat(),
            order.action.value,
            order.size,
            current_price,
            order.stop_loss,
            order.take_profit,
            order.reason,
        )
        # Giả lập khớp lệnh ngay tại giá hiện tại — dùng cho backtest/paper trading.
        return ExecutionResult(filled=True, fill_price=current_price, order=order)