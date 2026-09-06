from decision.base import MarketState, Action
from decision.trend_reversal import TrendReversalEngine


def _state(**overrides) -> MarketState:
    defaults = dict(
        close=100.0,
        timestamp=1_700_000_000,
        ema_fast=101.0,
        ema_mid=100.0,
        ema_slow=98.0,
        rsi_fast=70.0,
    )
    defaults.update(overrides)
    return MarketState(**defaults)


def test_hold_when_missing_required_fields():
    engine = TrendReversalEngine()
    state = _state(rsi_fast=None)

    signal = engine.decide(state)

    assert signal.action == Action.HOLD
    assert signal.is_reversal is False
    assert "Chưa đủ dữ liệu" in signal.reason


def test_first_valid_candle_is_always_a_reversal():
    # EMA: uptrend (101>100>98). RSI9=70 (>65) -> uptrend. Khớp nhau -> Uptrend.
    # Chưa có trạng thái nào được giữ trước đó -> đây luôn là điểm đảo chiều đầu tiên.
    engine = TrendReversalEngine()
    state = _state(ema_fast=101.0, ema_mid=100.0, ema_slow=98.0, rsi_fast=70.0)

    signal = engine.decide(state)

    assert signal.action == Action.BUY
    assert signal.is_reversal is True


def test_holds_state_without_new_reversal_while_unchanged():
    engine = TrendReversalEngine()
    state = _state(ema_fast=101.0, ema_mid=100.0, ema_slow=98.0, rsi_fast=70.0)

    first = engine.decide(state)
    second = engine.decide(state)  # cùng dữ liệu -> vẫn đang giữ Uptrend

    assert first.is_reversal is True
    assert second.is_reversal is False
    assert second.action == Action.HOLD


def test_sideways_when_ema50_between_ema9_and_ema21():
    # EMA50 (100) nằm giữa EMA9 (105) và EMA21 (95) -> Sideways theo định nghĩa mới
    engine = TrendReversalEngine()
    state = _state(ema_fast=105.0, ema_mid=95.0, ema_slow=100.0, rsi_fast=50.0)

    signal = engine.decide(state)

    assert signal.action == Action.HOLD
    assert signal.is_reversal is True  # lần đầu chuyển vào Sideways cũng là 1 lần đảo chiều


def test_reversal_from_uptrend_to_downtrend():
    engine = TrendReversalEngine()
    uptrend_state = _state(ema_fast=101.0, ema_mid=100.0, ema_slow=98.0, rsi_fast=70.0)
    engine.decide(uptrend_state)  # thiết lập trạng thái đang giữ = Uptrend

    downtrend_state = _state(
        timestamp=1_700_000_300,
        ema_fast=95.0, ema_mid=98.0, ema_slow=100.0, rsi_fast=30.0,
    )
    signal = engine.decide(downtrend_state)

    assert signal.action == Action.SELL
    assert signal.is_reversal is True
    assert "uptrend" in signal.reason
    assert "downtrend" in signal.reason


def test_no_reversal_when_ema_and_rsi_state_disagree_and_already_sideways():
    engine = TrendReversalEngine()
    sideways_state = _state(ema_fast=105.0, ema_mid=95.0, ema_slow=100.0, rsi_fast=50.0)
    engine.decide(sideways_state)  # thiết lập trạng thái đang giữ = Sideways

    # EMA nói uptrend nhưng RSI9=50 (vùng trung tính) -> không khớp -> vẫn Sideways
    disagreeing_state = _state(
        timestamp=1_700_000_300,
        ema_fast=101.0, ema_mid=100.0, ema_slow=98.0, rsi_fast=50.0,
    )
    signal = engine.decide(disagreeing_state)

    assert signal.action == Action.HOLD
    assert signal.is_reversal is False
