"""
Decision engine: phát hiện ĐIỂM ĐẢO CHIỀU giữa 3 trạng thái thị trường —
Uptrend / Downtrend / Sideways.

=== Trạng thái theo EMA (EMA9 / EMA21 / EMA50) ===
    Uptrend   : EMA9 > EMA21 > EMA50
    Downtrend : EMA9 < EMA21 < EMA50
    Sideways  : EMA50 nằm giữa EMA9 và EMA21 (bất kể EMA9/EMA21 ai lớn hơn),
                hoặc bất kỳ trường hợp nào khác không phải uptrend/downtrend.

=== Trạng thái theo RSI9 ===
    Uptrend   : RSI9 > 65
    Downtrend : RSI9 < 35
    Sideways  : 35 <= RSI9 <= 65

=== Trạng thái XÁC NHẬN tại một nến ===
    = trạng thái EMA nếu trạng thái EMA và trạng thái RSI9 TRÙNG NHAU
      (cùng Uptrend hoặc cùng Downtrend);
    = Sideways nếu 2 trạng thái không khớp nhau (kể cả khi 1 trong 2 đang
      là Sideways).

    ⚠️ Đây là một GIẢ ĐỊNH hợp lý về cách "kết hợp" EMA-state và RSI-state
    theo mô tả — nếu ý bạn khác (ví dụ RSI9 là điều kiện DUY NHẤT quyết
    định trạng thái, còn EMA chỉ tham khảo), báo lại để chỉnh logic
    `_confirm_state()` bên dưới cho đúng ý, các phần còn lại (giữ trạng
    thái, chỉ log khi đổi) không cần đổi.

=== Điểm đảo chiều & cơ chế "hold" ===
    Engine giữ trạng thái đã xác nhận gần nhất trong `self._held_state`.
    Một ĐIỂM ĐẢO CHIỀU chỉ xuất hiện khi trạng thái xác nhận tại nến hiện
    tại KHÁC với `self._held_state`:
      - Engine cập nhật `self._held_state` = trạng thái mới.
      - Trả về Signal với `is_reversal=True` (risk_manager sẽ ghi log kèm
        đúng timestamp của nến này).
    Ở các nến sau đó, nếu trạng thái xác nhận KHÔNG đổi, engine chỉ trả về
    HOLD với `is_reversal=False` — tức "giữ nguyên trạng thái", không log
    lặp lại — cho đến khi có tín hiệu đảo chiều kế tiếp.

MACD đã bị loại khỏi chiến lược này theo yêu cầu (tạm thời).
"""

from typing import Optional
from decision.base import DecisionEngine, MarketState, Signal, Action, TrendState

RSI_UPTREND_THRESHOLD = 65.0
RSI_DOWNTREND_THRESHOLD = 35.0

_STATE_TO_ACTION = {
    TrendState.UPTREND: Action.BUY,
    TrendState.DOWNTREND: Action.SELL,
    TrendState.SIDEWAYS: Action.HOLD,
}


def determine_ema_state(ema_fast: float, ema_mid: float, ema_slow: float) -> TrendState:
    if ema_fast > ema_mid > ema_slow:
        return TrendState.UPTREND
    if ema_fast < ema_mid < ema_slow:
        return TrendState.DOWNTREND
    return TrendState.SIDEWAYS


def determine_rsi_state(rsi_value: float) -> TrendState:
    if rsi_value > RSI_UPTREND_THRESHOLD:
        return TrendState.UPTREND
    if rsi_value < RSI_DOWNTREND_THRESHOLD:
        return TrendState.DOWNTREND
    return TrendState.SIDEWAYS


class TrendReversalEngine(DecisionEngine):
    """
    Yêu cầu MarketState phải có: ema_fast (EMA9), ema_mid (EMA21),
    ema_slow (EMA50), rsi_fast (RSI9). Thiếu bất kỳ trường nào -> HOLD,
    không cập nhật trạng thái đang giữ, không tính là đảo chiều.
    """

    def __init__(self):
        self._held_state: Optional[TrendState] = None

    def decide(self, state: MarketState) -> Signal:
        if (
            state.ema_fast is None
            or state.ema_mid is None
            or state.ema_slow is None
            or state.rsi_fast is None
        ):
            return Signal(
                Action.HOLD, confidence=0.0,
                reason="Chưa đủ dữ liệu EMA9/EMA21/EMA50 hoặc RSI9",
            )

        ema_state = determine_ema_state(state.ema_fast, state.ema_mid, state.ema_slow)
        rsi_state = determine_rsi_state(state.rsi_fast)
        confirmed_state = ema_state if ema_state == rsi_state else TrendState.SIDEWAYS

        if confirmed_state == self._held_state:
            return Signal(
                Action.HOLD, confidence=0.0,
                reason=f"Đang giữ trạng thái {self._held_state.value}",
                is_reversal=False,
            )

        previous_state = self._held_state
        self._held_state = confirmed_state

        return Signal(
            _STATE_TO_ACTION[confirmed_state],
            confidence=0.65 if confirmed_state != TrendState.SIDEWAYS else 0.0,
            reason=(
                f"Đảo chiều: {previous_state.value if previous_state else 'chưa xác định'} "
                f"-> {confirmed_state.value} (EMA={ema_state.value}, RSI9={rsi_state.value})"
            ),
            is_reversal=True,
        )
