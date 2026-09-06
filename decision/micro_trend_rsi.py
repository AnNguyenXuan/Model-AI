"""
Decision engine: Bắt sóng ngắn theo xu hướng vi mô (Micro-trend Following).

Cấu trúc 3 lớp đúng như đã thống nhất:
  Lớp 1 - Trend filter : EMA9 > EMA21 > EMA50 (uptrend) hoặc ngược lại (downtrend)
  Lớp 2 - Entry trigger : giá hồi về áp sát EMA9/EMA21 + RSI ngắn (7-9) hồi về
                          vùng hợp lệ (không cần chạm hẳn 30/70 như RSI chuẩn,
                          vì trong trend mạnh RSI hiếm khi xuống sâu)
  Lớp 3 - Xác nhận lực đẩy (tuỳ chọn): MACD histogram cùng chiều xu hướng

Engine này chỉ sinh tín hiệu VÀO LỆNH. Việc thoát lệnh/trailing theo EMA9
hoặc theo ATR (risk/risk_manager.py: atr_multiplier_sl) được xử lý ở lớp
risk — đúng nguyên tắc tách lớp của framework (xem docs/architecture.md):
decision không biết gì về size hay SL/TP.
"""

from decision.base import DecisionEngine, MarketState, Signal, Action

# Vùng RSI ngắn được coi là "hồi về hợp lệ" để vào lệnh theo đúng xu hướng.
# Uptrend: RSI hồi từ trên xuống nhưng chưa cắm sâu xuống vùng quá bán.
# Downtrend: RSI hồi từ dưới lên nhưng chưa cắm sâu lên vùng quá mua.
PULLBACK_ZONE_LONG = (35.0, 50.0)
PULLBACK_ZONE_SHORT = (50.0, 65.0)

# Khoảng cách tối đa (%) giữa giá đóng cửa và EMA9/EMA21 để coi là "áp sát"
# vùng hồi — nên tinh chỉnh theo biến động thực tế của khung giờ đang dùng.
MAX_DISTANCE_TO_EMA_PCT = 0.5


class MicroTrendRsiEngine(DecisionEngine):
    """
    Yêu cầu MarketState phải có: ema_fast (EMA9), ema_mid (EMA21), ema_50,
    rsi_fast (RSI chu kỳ ngắn, ví dụ 7). Thiếu bất kỳ trường nào -> HOLD.

    macd_hist là tuỳ chọn: chỉ được dùng làm bộ lọc xác nhận nếu
    `require_macd_confirmation=True`; nếu không, engine chỉ dùng Lớp 1 + 2.
    """

    def __init__(self, require_macd_confirmation: bool = False):
        self.require_macd_confirmation = require_macd_confirmation

    def decide(self, state: MarketState) -> Signal:
        if (
            state.ema_fast is None
            or state.ema_mid is None
            or state.ema_50 is None
            or state.rsi_fast is None
        ):
            return Signal(
                Action.HOLD, confidence=0.0,
                reason="Chưa đủ dữ liệu EMA9/EMA21/EMA50 hoặc RSI ngắn",
            )

        uptrend = state.ema_fast > state.ema_mid > state.ema_50
        downtrend = state.ema_fast < state.ema_mid < state.ema_50

        if not uptrend and not downtrend:
            return Signal(
                Action.HOLD, confidence=0.0,
                reason="EMA9/21/50 chưa xếp lớp rõ xu hướng (thị trường đi ngang)",
            )

        near_pullback_zone = self._is_price_near_ema(
            state.close, state.ema_fast, state.ema_mid
        )

        if uptrend:
            rsi_in_zone = PULLBACK_ZONE_LONG[0] <= state.rsi_fast <= PULLBACK_ZONE_LONG[1]
            if not (near_pullback_zone and rsi_in_zone):
                return Signal(
                    Action.HOLD, confidence=0.0,
                    reason="Đang uptrend vi mô nhưng chưa có điểm hồi hợp lệ",
                )
            if self.require_macd_confirmation and not self._macd_confirms(state, bullish=True):
                return Signal(
                    Action.HOLD, confidence=0.0,
                    reason="Setup mua hợp lệ nhưng MACD chưa xác nhận lực đẩy",
                )
            return Signal(
                Action.BUY, confidence=0.65,
                reason="Uptrend vi mô (EMA9>EMA21>EMA50), giá hồi về EMA + RSI ngắn hồi vùng 35-50",
            )

        # downtrend
        rsi_in_zone = PULLBACK_ZONE_SHORT[0] <= state.rsi_fast <= PULLBACK_ZONE_SHORT[1]
        if not (near_pullback_zone and rsi_in_zone):
            return Signal(
                Action.HOLD, confidence=0.0,
                reason="Đang downtrend vi mô nhưng chưa có điểm hồi hợp lệ",
            )
        if self.require_macd_confirmation and not self._macd_confirms(state, bullish=False):
            return Signal(
                Action.HOLD, confidence=0.0,
                reason="Setup bán hợp lệ nhưng MACD chưa xác nhận lực đẩy",
            )
        return Signal(
            Action.SELL, confidence=0.65,
            reason="Downtrend vi mô (EMA9<EMA21<EMA50), giá hồi về EMA + RSI ngắn hồi vùng 50-65",
        )

    @staticmethod
    def _is_price_near_ema(close: float, ema_fast: float, ema_mid: float) -> bool:
        """Giá được coi là 'áp sát' vùng hồi nếu nằm giữa EMA9/EMA21, hoặc
        lệch không quá MAX_DISTANCE_TO_EMA_PCT % so với EMA9."""
        lower, upper = min(ema_fast, ema_mid), max(ema_fast, ema_mid)
        if lower <= close <= upper:
            return True
        if ema_fast == 0:
            return False
        distance_pct = abs(close - ema_fast) / abs(ema_fast) * 100
        return distance_pct <= MAX_DISTANCE_TO_EMA_PCT

    @staticmethod
    def _macd_confirms(state: MarketState, bullish: bool) -> bool:
        if state.macd_hist is None:
            return False
        return state.macd_hist > 0 if bullish else state.macd_hist < 0
