"""
Lấy dữ liệu giá thô (OHLCV) từ sàn hoặc file lịch sử.

Chỉ chịu trách nhiệm lấy dữ liệu — không làm sạch, không tính chỉ báo.
Việc đó thuộc về `data/pipeline.py`.
"""
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import requests


@dataclass
class Candle:
    timestamp: int  # epoch seconds (UTC). Chỉ được format thành ngày giờ khi ghi/đọc CSV.
    open: float
    high: float
    low: float
    close: float
    volume: float

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
DEFAULT_CACHE_DIR = "data/cache"
_CSV_FIELDS = ["timestamp", "open", "high", "low", "close", "volume"]
_VALID_INTERVALS = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M",
}

# Định dạng ngày giờ dùng khi lưu CSV. Giờ UTC để khớp với timestamp gốc từ Binance.
_TS_FORMAT = "%Y-%m-%d %H:%M:%S"


def fetch_historical(
    symbol: str,
    timeframe: str,
    lookback_bars: int,
    cache_dir: str = DEFAULT_CACHE_DIR,
    force_refresh: bool = False,
) -> List[Candle]:
    """
    Lấy `lookback_bars` nến gần nhất cho `symbol` ở khung `timeframe`.

    Logic cache: nếu file CSV tại `cache_dir/{symbol}_{timeframe}.csv` đã có
    đủ `lookback_bars` nến (và không bật `force_refresh`) -> đọc thẳng từ
    CSV, KHÔNG gọi Binance API. Ngược lại, chỉ gọi API để lấy phần còn
    thiếu, gộp với cache cũ, loại trùng theo timestamp, rồi ghi đè lại CSV.
    """
    if timeframe not in _VALID_INTERVALS:
        raise ValueError(
            f"Timeframe '{timeframe}' không hợp lệ với Binance. "
            f"Các giá trị hợp lệ: {sorted(_VALID_INTERVALS)}"
        )

    path = _cache_path(symbol, timeframe, cache_dir)
    cached = [] if force_refresh else _load_cache(path)

    if cached and len(cached) >= lookback_bars:
        return cached[-lookback_bars:]

    all_candles = list(cached)
    remaining = lookback_bars - len(cached)
    end_time_ms = cached[0].timestamp * 1000 - 1 if cached else None

    while remaining > 0:
        limit = min(remaining, 1000)
        batch = _fetch_klines_from_api(symbol, timeframe, limit, end_time_ms)
        if not batch:
            break
        all_candles = batch + all_candles
        remaining -= len(batch)
        end_time_ms = batch[0].timestamp * 1000 - 1
        if len(batch) < limit:
            break  # sàn không còn dữ liệu cũ hơn

    all_candles = _dedup_sorted(all_candles)
    _save_cache(path, all_candles)
    return all_candles[-lookback_bars:]


# --- helpers định dạng thời gian ---

def _ts_to_str(ts: int) -> str:
    """Epoch giây (UTC) -> chuỗi 'YYYY-MM-DD HH:MM:SS' để lưu vào CSV."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(_TS_FORMAT)


def _str_to_ts(value: str) -> int:
    """Chuỗi ngày giờ trong CSV -> epoch giây (UTC).

    Hỗ trợ ngược với cache cũ: nếu giá trị vẫn là số epoch (từ file được
    tạo trước khi có thay đổi này), parse thẳng thành int mà không lỗi.
    """
    value = value.strip()
    try:
        return int(value)
    except ValueError:
        dt = datetime.strptime(value, _TS_FORMAT).replace(tzinfo=timezone.utc)
        return int(dt.timestamp())


# --- helpers dùng bởi fetch_historical ---

def _cache_path(symbol: str, timeframe: str, cache_dir: str) -> Path:
    return Path(cache_dir) / f"{symbol.upper()}_{timeframe}.csv"


def _load_cache(path: Path) -> List[Candle]:
    if not path.exists():
        return []
    candles: List[Candle] = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            candles.append(Candle(
                timestamp=_str_to_ts(row["timestamp"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            ))
    return _dedup_sorted(candles)


def _save_cache(path: Path, candles: List[Candle]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for c in candles:
            row = asdict(c)
            row["timestamp"] = _ts_to_str(c.timestamp)
            writer.writerow(row)


def _dedup_sorted(candles: List[Candle]) -> List[Candle]:
    by_ts = {c.timestamp: c for c in candles}
    return sorted(by_ts.values(), key=lambda c: c.timestamp)


def _fetch_klines_from_api(
    symbol: str, timeframe: str, limit: int, end_time_ms: Optional[int]
) -> List[Candle]:
    params = {"symbol": symbol.upper(), "interval": timeframe, "limit": limit}
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=10)
    resp.raise_for_status()
    rows = resp.json()
    return [
        Candle(
            timestamp=int(row[0] // 1000),
            open=float(row[1]), high=float(row[2]),
            low=float(row[3]), close=float(row[4]), volume=float(row[5]),
        )
        for row in rows
    ]


def fetch_latest_candle(symbol: str, timeframe: str) -> Candle:
    """Lấy nến mới nhất — dùng cho vòng lặp live, không dùng trong backtest."""
    raise NotImplementedError("Cắm nguồn dữ liệu real-time vào đây.")