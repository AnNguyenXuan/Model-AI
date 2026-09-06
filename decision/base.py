"""
Interface chung mà MỌI decision engine (rule-based, ML, RL) phải implement.

Nhờ interface này, main.py và backtest engine không cần biết bên trong
decision engine là gì — chỉ cần gọi `.decide(state)`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Action(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class TrendState(Enum):
    """
    3 trạng thái thị trường duy nhất mà chiến lược đảo chiều
    (decision/trend_reversal.py) sử dụng.
    """
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"


@dataclass
class MarketState:
    """Trạng thái thị trường tại một thời điểm, đầu vào cho decision engine."""
    close: float
    timestamp: int  # epoch giây (UTC) của nến — cần để risk log đúng thời điểm

    # --- Dùng bởi TrendReversalEngine (decision/trend_reversal.py) ---
    ema_fast: Optional[float] = None   # EMA9  — Lớp 1: xác định trạng thái
    ema_mid: Optional[float] = None    # EMA21 — Lớp 1: xác định trạng thái
    ema_slow: Optional[float] = None   # EMA50 — Lớp 1: xác định trạng thái
    rsi_fast: Optional[float] = None   # RSI9  — Lớp 2: xác nhận điểm đảo chiều

    regime: str = "unknown"  # nhãn từ llm_filter, có thể bỏ qua nếu engine không dùng


@dataclass
class Signal:
    action: Action
    confidence: float  # 0.0 - 1.0
    reason: str          # để log, debug tại sao có tín hiệu
    is_reversal: bool = False  # True nếu đây chính là nến xuất hiện điểm đảo chiều


class DecisionEngine(ABC):
    @abstractmethod
    def decide(self, state: MarketState) -> Signal:
        """Nhận trạng thái thị trường, trả về tín hiệu BUY/SELL/HOLD."""
        raise NotImplementedError
