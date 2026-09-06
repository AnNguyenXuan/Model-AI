from dataclasses import dataclass
from features.indicators import rsi


@dataclass
class _FakeCandle:
    close: float
    # Các trường khác không dùng tới trong rsi(), thêm cho đủ shape của Candle thật
    timestamp: int = 0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: float = 0.0


def _candles(closes):
    return [_FakeCandle(close=c) for c in closes]


def test_rsi_returns_none_before_enough_data():
    candles = _candles([1, 2, 3])  # period=14 mặc định, chưa đủ dữ liệu
    result = rsi(candles, period=14)
    assert all(v is None for v in result)


def test_rsi_is_100_when_all_moves_are_gains():
    # Giá tăng liên tục -> Average Loss = 0 -> RSI = 100
    closes = list(range(1, 20))  # 1..19, toàn tăng
    candles = _candles(closes)
    result = rsi(candles, period=14)
    assert result[14] == 100.0


def test_rsi_wilder_first_value_matches_manual_calculation():
    # 15 nến: đổi giá thủ công để tính tay Average Gain/Loss đầu tiên (period=14)
    closes = [100, 101, 102, 101, 103, 104, 103, 105, 106, 105, 107, 108, 107, 109, 110]
    candles = _candles(closes)
    result = rsi(candles, period=14)

    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(c, 0) for c in changes]
    losses = [max(-c, 0) for c in changes]
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    expected_rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss else 100.0

    assert result[14] is not None
    assert round(result[14], 6) == round(expected_rsi, 6)


def test_rsi_stays_within_0_100_bounds():
    closes = [100 + (i % 5) - 2 for i in range(50)]  # dao động ngẫu nhiên nhẹ
    candles = _candles(closes)
    result = rsi(candles, period=14)
    for v in result:
        if v is not None:
            assert 0.0 <= v <= 100.0
