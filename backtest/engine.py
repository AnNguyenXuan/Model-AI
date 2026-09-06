"""
Backtest engine chạy TUẦN TỰ từng nến — tại mỗi bước chỉ được dùng dữ liệu
tại và trước nến đó. Đây là điểm quan trọng nhất để tránh lookahead bias.
"""

from typing import List, Optional
from data.fetch import Candle
from decision.base import DecisionEngine, MarketState
from risk.risk_manager import RiskManager
from execution.logger_execution import LoggerExecution


def run_backtest(
    candles: List[Candle],
    ema_20_series: List[float],
    ema_50_series: List[float],
    atr_series: List[float],
    engine: DecisionEngine,
    risk_manager: RiskManager,
    execution: LoggerExecution,
    rsi_14_series: Optional[List[float]] = None,
    ema_fast_series: Optional[List[float]] = None,
    ema_mid_series: Optional[List[float]] = None,
    rsi_fast_series: Optional[List[float]] = None,
    macd_hist_series: Optional[List[float]] = None,
) -> List[dict]:
    """
    Chạy backtest tuần tự. Trả về danh sách kết quả từng nến để tính metrics
    ở backtest/metrics.py.

    LƯU Ý: candles[i] chỉ được ghép với ema_20_series[i], atr_series[i]...
    tức là chỉ báo tại đúng nến đó — không lệch chỉ số, không nhìn về
    phía trước.

    Các tham số `rsi_14_series`, `ema_fast_series`, `ema_mid_series`,
    `rsi_fast_series`, `macd_hist_series` là TUỲ CHỌN (mặc định None) —
    lời gọi cũ (chỉ dùng EmaCrossoverEngine) không cần đổi gì vẫn chạy
    đúng như trước. Muốn dùng MicroTrendRsiEngine (EMA9/21/50 + RSI ngắn),
    truyền thêm các series này (xem main.py).
    """
    results = []
    for i, candle in enumerate(candles):
        state = MarketState(
            close=candle.close,
            ema_20=ema_20_series[i],
            ema_50=ema_50_series[i],
            rsi_14=rsi_14_series[i] if rsi_14_series is not None else None,
            atr_14=atr_series[i],
            ema_fast=ema_fast_series[i] if ema_fast_series is not None else None,
            ema_mid=ema_mid_series[i] if ema_mid_series is not None else None,
            rsi_fast=rsi_fast_series[i] if rsi_fast_series is not None else None,
            macd_hist=macd_hist_series[i] if macd_hist_series is not None else None,
        )
        signal = engine.decide(state)
        order = risk_manager.build_order(signal, entry_price=candle.close,
                                          atr_value=atr_series[i] or 0.0)
        result = execution.send_order(order, current_price=candle.close)

        results.append({
            "timestamp": candle.timestamp,
            "signal": signal,
            "order": order,
            "execution": result,
        })

    return results
