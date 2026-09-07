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


@dataclass
class DataRequest:
    """
    Cấu trúc chuẩn hoá tham số cho một lần lấy dữ liệu — dùng làm "hợp đồng"
    giữa config.yaml/CLI và fetch_historical(), thay vì main.py phải tự tra
    cfg["x"]["y"] rồi truyền theo vị trí.
    """
    symbol: str
    timeframe: str
    lookback_bars: int
    anchor_time: Optional[datetime] = None
    force_refresh: bool = False


def build_data_request(
    cfg: dict, anchor_time_override: Optional[datetime] = None
) -> DataRequest:
    """
    Gom tham số cần cho fetch_historical từ config.yaml thành một DataRequest.

    - anchor_time có thể khai báo trong config.yaml tại `data.anchor_time`
      (chuỗi UTC dạng "YYYY-MM-DD HH:MM:SS") để cố định mốc lấy dữ liệu.
    - anchor_time_override (thường lấy từ CLI --anchor-time) LUÔN ưu tiên
      hơn giá trị trong config.yaml nếu được truyền vào.
    - Không khai báo gì ở cả hai nơi -> anchor_time=None -> lấy realtime.
    """
    data_cfg = cfg["data"]

    anchor_time = anchor_time_override
    if anchor_time is None and data_cfg.get("anchor_time"):
        anchor_time = datetime.strptime(
            data_cfg["anchor_time"], _TS_FORMAT
        ).replace(tzinfo=timezone.utc)

    return DataRequest(
        symbol=cfg["symbol"],
        timeframe=cfg["timeframe"],
        lookback_bars=data_cfg["lookback_bars"],
        anchor_time=anchor_time,
        force_refresh=data_cfg.get("force_refresh", False),
    )


def fetch_from_request(req: DataRequest) -> List[Candle]:
    """Điểm gọi chuẩn cho main.py — nhận một DataRequest thay vì tham số rời."""
    return fetch_historical(
        symbol=req.symbol,
        timeframe=req.timeframe,
        lookback_bars=req.lookback_bars,
        anchor_time=req.anchor_time,
        force_refresh=req.force_refresh,
    )


def fetch_historical(
    symbol: str,
    timeframe: str,
    lookback_bars: int,
    cache_dir: str = DEFAULT_CACHE_DIR,
    force_refresh: bool = False,
    anchor_time: Optional[datetime] = None,
) -> List[Candle]:
    """
    Lấy `lookback_bars` nến gần nhất cho `symbol` ở khung `timeframe`, tính
    lùi về từ `anchor_time`.

    - anchor_time=None       -> REALTIME: tính từ hiện tại, dùng cache CSV
      tại `cache_dir/{symbol}_{timeframe}.csv` (hành vi y hệt bản gốc).
    - anchor_time=<datetime> -> THEO MỐC: tính lùi về từ đúng mốc đó, KHÔNG
      dùng cache realtime (mỗi mốc cho kết quả khác nhau, dùng chung cache
      sẽ trộn lẫn dữ liệu của các mốc khác nhau).

    Logic cache (chỉ áp dụng nhánh realtime): nếu file CSV đã có đủ
    `lookback_bars` nến (và không bật `force_refresh`) -> đọc thẳng từ CSV,
    KHÔNG gọi Binance API. Ngược lại, chỉ gọi API để lấy phần còn thiếu,
    gộp với cache cũ, loại trùng theo timestamp, rồi ghi đè lại CSV.
    """
    if timeframe not in _VALID_INTERVALS:
        raise ValueError(
            f"Timeframe '{timeframe}' không hợp lệ với Binance. "
            f"Các giá trị hợp lệ: {sorted(_VALID_INTERVALS)}"
        )

    # --- Nhánh THEO MỐC: không đụng tới cache realtime ---
    if anchor_time is not None:
        end_time_ms = int(anchor_time.timestamp() * 1000)
        all_candles: List[Candle] = []
        remaining = lookback_bars
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
        return _dedup_sorted(all_candles)[-lookback_bars:]

    # --- Nhánh REALTIME: giữ nguyên logic cache gốc ---
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