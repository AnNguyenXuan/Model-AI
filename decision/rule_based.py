"""
Decision engine đơn giản nhất: EMA crossover.

Dùng để kiểm chứng toàn bộ pipeline (data -> feature -> decision -> risk ->
execution -> backtest) chạy đúng trước khi thử ML hay RL.
"""

from decision.base import DecisionEngine, MarketState, Signal, Action


class EmaCrossoverEngine(DecisionEngine):
    def decide(self, state: MarketState) -> Signal:
        if state.ema_20 is None or state.ema_50 is None:
            return Signal(Action.HOLD, confidence=0.0, reason="Chưa đủ dữ liệu EMA")

        if state.ema_20 > state.ema_50:
            return Signal(Action.BUY, confidence=0.6, reason="EMA20 cắt lên trên EMA50")
        elif state.ema_20 < state.ema_50:
            return Signal(Action.SELL, confidence=0.6, reason="EMA20 cắt xuống dưới EMA50")
        return Signal(Action.HOLD, confidence=0.0, reason="EMA20 và EMA50 gần bằng nhau")
