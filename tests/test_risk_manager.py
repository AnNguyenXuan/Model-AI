from risk.risk_manager import RiskManager
from decision.base import Signal, Action


def test_build_order_buy_sets_correct_stop_loss():
    rm = RiskManager(capital=10000, risk_per_trade_pct=1.0,
                      atr_multiplier_sl=2.0, max_drawdown_pct=20.0)
    signal = Signal(Action.BUY, confidence=0.6, reason="test")
    order = rm.build_order(signal, entry_price=100.0, atr_value=2.0)

    assert order.action == Action.BUY
    assert order.stop_loss == 100.0 - 2.0 * 2.0
    assert order.take_profit == 100.0 + 2.0 * 2.0 * 2


def test_trading_halted_when_drawdown_exceeds_limit():
    rm = RiskManager(capital=10000, risk_per_trade_pct=1.0,
                      atr_multiplier_sl=2.0, max_drawdown_pct=10.0)
    rm.update_capital(8500)  # drawdown 15% > 10%
    signal = Signal(Action.BUY, confidence=0.6, reason="test")
    order = rm.build_order(signal, entry_price=100.0, atr_value=2.0)

    assert order.action == Action.HOLD
