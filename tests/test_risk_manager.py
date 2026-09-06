import logging

from risk.risk_manager import RiskManager
from decision.base import Signal, Action


def test_build_order_returns_action_and_reason_without_sizing(tmp_path):
    rm = RiskManager(log_path=str(tmp_path / "reversals.log"))
    signal = Signal(Action.BUY, confidence=0.6, reason="test", is_reversal=True)

    order = rm.build_order(signal, timestamp=1_700_000_000)

    assert order.action == Action.BUY
    assert order.reason == "test"
    assert order.is_reversal is True
    assert not hasattr(order, "stop_loss")
    assert not hasattr(order, "take_profit")
    assert not hasattr(order, "size")


def test_build_order_logs_only_when_is_reversal(tmp_path):
    log_path = tmp_path / "reversals.log"
    rm = RiskManager(log_path=str(log_path))

    non_reversal = Signal(Action.HOLD, confidence=0.0, reason="giữ trạng thái", is_reversal=False)
    rm.build_order(non_reversal, timestamp=1_700_000_000)

    reversal = Signal(Action.SELL, confidence=0.65, reason="đảo chiều xuống", is_reversal=True)
    rm.build_order(reversal, timestamp=1_700_000_300)

    for handler in rm.logger.handlers:
        handler.flush()

    content = log_path.read_text(encoding="utf-8")
    assert "đảo chiều xuống" in content
    assert "giữ trạng thái" not in content
