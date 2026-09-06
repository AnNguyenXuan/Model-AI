"""
Backtest engine chạy TUẦN TỰ từng nến — tại mỗi bước chỉ được dùng dữ liệu
tại và trước nến đó. Đây là điểm quan trọng nhất để tránh lookahead bias.
"""

from typing import Dict, List
from data.fetch import Candle
from decision.base import DecisionEngine, MarketState
from risk.risk_manager import RiskManager


def run_backtest(
    candles: List[Candle],
    features: Dict[str, list],
    engine: DecisionEngine,
    risk_manager: RiskManager,
) -> List[dict]:
    """
    Chạy backtest tuần tự, trả về danh sách kết quả từng nến.

    `features`: dict {tên_field: series}, ví dụ
        {"ema_fast": [...], "ema_mid": [...], "ema_slow": [...], "rsi_fast": [...]}
    lấy từ `features.registry.build_features()`. Tên key PHẢI trùng tên
    field tương ứng trong `decision.base.MarketState` để build đúng state.

    LƯU Ý: candles[i] chỉ được ghép với features[<tên>][i] — chỉ báo tại
    đúng nến đó, không lệch chỉ số, không nhìn về phía trước.

    Giai đoạn hiện tại: chưa có size/SL/TP (xem risk/risk_manager.py),
    engine chỉ sinh Signal và risk_manager chỉ log khi có điểm đảo chiều.
    """
    results = []
    for i, candle in enumerate(candles):
        state_kwargs = {name: series[i] for name, series in features.items()}
        state = MarketState(close=candle.close, timestamp=candle.timestamp, **state_kwargs)

        signal = engine.decide(state)
        order = risk_manager.build_order(signal, timestamp=candle.timestamp)

        results.append({
            "timestamp": candle.timestamp,
            "signal": signal,
            "order": order,
        })

    return results
