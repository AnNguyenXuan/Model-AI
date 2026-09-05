"""
Tính các chỉ số đánh giá hiệu quả từ kết quả backtest: PnL, Sharpe, drawdown, win rate.
"""

from typing import List
import math


def compute_pnl_series(equity_curve: List[float]) -> List[float]:
    """Chuỗi lợi nhuận theo từng bước, dùng để tính Sharpe."""
    return [equity_curve[i] - equity_curve[i - 1] for i in range(1, len(equity_curve))]


def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    if not returns:
        return 0.0
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (mean_return - risk_free_rate) / std


def max_drawdown_pct(equity_curve: List[float]) -> float:
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        dd = (peak - value) / peak * 100 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def win_rate(pnl_per_trade: List[float]) -> float:
    if not pnl_per_trade:
        return 0.0
    wins = sum(1 for pnl in pnl_per_trade if pnl > 0)
    return wins / len(pnl_per_trade) * 100
