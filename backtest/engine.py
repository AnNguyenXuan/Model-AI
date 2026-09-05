"""
Backtest engine chạy TUẦN TỰ từng nến — tại mỗi bước chỉ được dùng dữ liệu
tại và trước nến đó. Đây là điểm quan trọng nhất để tránh lookahead bias.
"""

from typing import List
from data.fetch import Candle
from decision.base import DecisionEngine, MarketState
from risk.risk_manager import RiskManager
from execution.logger_execution import LoggerExecution


def run_backtest(
    candles: List[Candle],
    ema_20_series: List[float],
    ema_50_series: List[float],
    engine: DecisionEngine,
    risk_manager: RiskManager,
    execution: LoggerExecution,
) -> List[dict]:
    """
    Chạy backtest tuần tự. Trả về danh sách kết quả từng nến để tính metrics
    ở backtest/metrics.py.

    LƯU Ý: candles[i] chỉ được ghép với ema_20_series[i], atr_series[i]...
    tức là chỉ báo tại đúng nến đó — không lệch chỉ số, không nhìn về
    phía trước.
    """
    results = []
    for i, candle in enumerate(candles):
        state = MarketState(
            close=candle.close,
            ema_20=ema_20_series[i],
            ema_50=ema_50_series[i],
            rsi_14=None,
        )
        signal = engine.decide(state)
        order = risk_manager.build_order(signal, entry_price=candle.close)
        result = execution.send_order(order, current_price=candle.close)

        results.append({
            "timestamp": candle.timestamp,
            "signal": signal,
            "order": order,
            "execution": result,
        })

    return results
