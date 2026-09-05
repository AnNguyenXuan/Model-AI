"""
Chuyển Signal (từ decision engine) thành Order cụ thể, kèm stop-loss/take-profit
và kiểm tra giới hạn drawdown tổng.
"""

from dataclasses import dataclass
from decision.base import Signal, Action
from risk.position_sizing import size_by_atr


@dataclass
class Order:
    action: Action
    size: float
    stop_loss: float
    take_profit: float
    reason: str


class RiskManager:
    def __init__(self, capital: float, risk_per_trade_pct: float,
                 atr_multiplier_sl: float, max_drawdown_pct: float):
        self.capital = capital
        self.peak_capital = capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.atr_multiplier_sl = atr_multiplier_sl
        self.max_drawdown_pct = max_drawdown_pct

    def current_drawdown_pct(self) -> float:
        if self.peak_capital == 0:
            return 0.0
        return (self.peak_capital - self.capital) / self.peak_capital * 100

    def is_trading_halted(self) -> bool:
        """Dừng mở lệnh mới nếu drawdown vượt ngưỡng cho phép."""
        return self.current_drawdown_pct() >= self.max_drawdown_pct

    def build_order(self, signal: Signal, entry_price: float, atr_value: float) -> Order:
        if signal.action == Action.HOLD or self.is_trading_halted():
            return Order(Action.HOLD, size=0.0, stop_loss=0.0, take_profit=0.0,
                         reason="Không vào lệnh: HOLD hoặc đã chạm giới hạn drawdown")

        size = size_by_atr(self.capital, self.risk_per_trade_pct, entry_price,
                            atr_value, self.atr_multiplier_sl)
        stop_distance = atr_value * self.atr_multiplier_sl
        if signal.action == Action.BUY:
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + stop_distance * 2  # R:R mặc định 1:2
        else:
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - stop_distance * 2

        return Order(signal.action, size, stop_loss, take_profit, signal.reason)

    def update_capital(self, new_capital: float):
        self.capital = new_capital
        self.peak_capital = max(self.peak_capital, new_capital)
