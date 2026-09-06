"""
Registry ánh xạ TÊN HÀM (dùng trong config.yaml) -> hàm tính thật trong
features/indicators.py.

Nhờ registry này, config chỉ cần khai báo tên hàm sẽ dùng (vd "ema",
"rsi", "macd") thay vì mã hoá cứng period vào tên biến (vd "ema_20",
"rsi_14" như trước) — tên field/alias và tên hàm tách rời nhau, 1 hàm có
thể được gọi nhiều lần với tham số khác nhau (vd `ema` dùng cho cả
ema_fast period=9 và ema_mid period=21).

Muốn thêm chỉ báo mới: viết hàm `def ten_ham(candles, **params)` trong
features/indicators.py rồi thêm 1 dòng vào INDICATOR_REGISTRY bên dưới —
không cần sửa gì ở build_features, main.py hay config.yaml.
"""

from typing import Callable, Dict, List
from data.fetch import Candle
from features.indicators import ema, rsi, macd

INDICATOR_REGISTRY: Dict[str, Callable] = {
    "ema": ema,
    "rsi": rsi,
    "macd": macd,
}


def build_features(candles: List[Candle], indicator_specs: dict) -> Dict[str, list]:
    """
    `indicator_specs` chính là `cfg["features"]["indicators"]` trong
    config.yaml, dạng:

        ema_fast:
          func: ema
          period: 9
        rsi_fast:
          func: rsi
          period: 9

    Trả về dict {alias: series}, vd {"ema_fast": [...], "rsi_fast": [...]}.
    `alias` (key ngoài cùng) do người dùng tự đặt tên, dùng để map thẳng
    vào field cùng tên trong `decision.base.MarketState` (xem
    backtest/engine.py) — vì vậy alias PHẢI trùng tên field MarketState
    tương ứng nếu muốn decision engine đọc được.
    """
    features: Dict[str, list] = {}
    for alias, spec in indicator_specs.items():
        spec = dict(spec)  # tránh sửa config gốc khi pop
        func_name = spec.pop("func", None)
        if func_name is None:
            raise ValueError(f"Feature '{alias}' thiếu khoá 'func' trong config.yaml")

        func = INDICATOR_REGISTRY.get(func_name)
        if func is None:
            raise ValueError(
                f"Indicator '{func_name}' (feature '{alias}') chưa được đăng ký "
                f"trong INDICATOR_REGISTRY (features/registry.py). "
                f"Các tên hợp lệ: {sorted(INDICATOR_REGISTRY)}"
            )

        features[alias] = func(candles, **spec)

    return features
