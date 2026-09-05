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


@dataclass
class MarketState:
    """Trạng thái thị trường tại một thời điểm, đầu vào cho decision engine."""
    close: float
    ema_20: Optional[float]
    ema_50: Optional[float]
    rsi_14: Optional[float]
    atr_14: Optional[float]
    regime: str = "unknown"  # nhãn từ llm_filter, có thể bỏ qua nếu engine không dùng


@dataclass
class Signal:
    action: Action
    confidence: float  # 0.0 - 1.0, dùng cho position sizing
    reason: str         # để log, debug tại sao vào lệnh


class DecisionEngine(ABC):
    @abstractmethod
    def decide(self, state: MarketState) -> Signal:
        """Nhận trạng thái thị trường, trả về tín hiệu BUY/SELL/HOLD."""
        raise NotImplementedError
