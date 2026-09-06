from decision.base import MarketState, Action
from decision.micro_trend_rsi import MicroTrendRsiEngine


def _state(**overrides) -> MarketState:
    defaults = dict(
        close=100.0,
        ema_20=None,
        ema_50=100.0,
        rsi_14=None,
        atr_14=1.0,
        ema_fast=100.5,
        ema_mid=99.5,
        rsi_fast=45.0,
    )
    defaults.update(overrides)
    return MarketState(**defaults)


def test_buy_when_uptrend_and_valid_pullback():
    engine = MicroTrendRsiEngine()
    # EMA9 > EMA21 > EMA50, giá nằm giữa EMA9/EMA21, RSI7 hồi về 45 (trong vùng 35-50)
    state = _state(ema_fast=101.0, ema_mid=100.0, ema_50=98.0, close=100.5, rsi_fast=45.0)

    signal = engine.decide(state)

    assert signal.action == Action.BUY
    assert signal.confidence > 0


def test_sell_when_downtrend_and_valid_pullback():
    engine = MicroTrendRsiEngine()
    # EMA9 < EMA21 < EMA50, giá nằm giữa EMA9/EMA21, RSI7 hồi lên 55 (trong vùng 50-65)
    state = _state(ema_fast=99.0, ema_mid=100.0, ema_50=102.0, close=99.5, rsi_fast=55.0)

    signal = engine.decide(state)

    assert signal.action == Action.SELL
    assert signal.confidence > 0


def test_hold_when_sideway_no_clear_trend():
    engine = MicroTrendRsiEngine()
    # EMA9/21/50 không xếp lớp rõ ràng -> không có xu hướng vi mô
    state = _state(ema_fast=100.0, ema_mid=101.0, ema_50=100.5, close=100.2, rsi_fast=45.0)

    signal = engine.decide(state)

    assert signal.action == Action.HOLD


def test_hold_when_uptrend_but_rsi_not_in_pullback_zone():
    engine = MicroTrendRsiEngine()
    # Xu hướng tăng rõ nhưng RSI7 đang ở 75 (quá mua) -> chưa phải điểm hồi hợp lệ
    state = _state(ema_fast=101.0, ema_mid=100.0, ema_50=98.0, close=100.5, rsi_fast=75.0)

    signal = engine.decide(state)

    assert signal.action == Action.HOLD


def test_hold_when_missing_required_fields():
    engine = MicroTrendRsiEngine()
    state = _state(rsi_fast=None)

    signal = engine.decide(state)

    assert signal.action == Action.HOLD
    assert "Chưa đủ dữ liệu" in signal.reason


def test_macd_confirmation_blocks_signal_when_required_and_missing():
    engine = MicroTrendRsiEngine(require_macd_confirmation=True)
    state = _state(ema_fast=101.0, ema_mid=100.0, ema_50=98.0, close=100.5,
                    rsi_fast=45.0, macd_hist=None)

    signal = engine.decide(state)

    assert signal.action == Action.HOLD
    assert "MACD" in signal.reason


def test_macd_confirmation_allows_signal_when_aligned():
    engine = MicroTrendRsiEngine(require_macd_confirmation=True)
    state = _state(ema_fast=101.0, ema_mid=100.0, ema_50=98.0, close=100.5,
                    rsi_fast=45.0, macd_hist=0.5)

    signal = engine.decide(state)

    assert signal.action == Action.BUY
