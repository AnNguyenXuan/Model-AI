"""
Tính khối lượng lệnh dựa trên volatility (ATR), không dùng % vốn cố định.
"""


def size_by_atr(
    capital: float,
    risk_per_trade_pct: float,
    entry_price: float,
    atr_value: float,
    atr_multiplier_sl: float,
) -> float:
    """
    Công thức: risk_amount = capital * risk_per_trade_pct%
    stop_distance = atr_value * atr_multiplier_sl
    size = risk_amount / stop_distance
    """
    if atr_value is None or atr_value <= 0:
        return 0.0
    risk_amount = capital * (risk_per_trade_pct / 100)
    stop_distance = atr_value * atr_multiplier_sl
    return risk_amount / stop_distance
