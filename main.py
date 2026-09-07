"""
Điểm khởi chạy — nối tất cả các lớp lại với nhau theo config.yaml.

    python main.py --mode backtest --config config/config.yaml
    python main.py --mode backtest --config config/config.yaml --anchor-time "2026-06-15 00:00:00"

Giai đoạn hiện tại: pipeline chỉ sinh TÍN HIỆU đảo chiều (BUY/SELL/HOLD),
CHƯA tính size/SL/TP (xem risk/risk_manager.py). Xem docs/roadmap.md giai
đoạn 2 khi cần thêm quản lý vốn.
"""

import argparse
from datetime import datetime, timezone

import yaml

from data.fetch import build_data_request, fetch_from_request
from data.pipeline import clean_candles
from features.registry import build_features
from decision.trend_reversal import TrendReversalEngine
from risk.risk_manager import RiskManager
from backtest.engine import run_backtest
from features.feature_logger import log_features


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_anchor_time(value: str) -> datetime:
    """CLI truyền chuỗi 'YYYY-MM-DD HH:MM:SS' (giờ UTC) -> datetime có tzinfo."""
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def build_decision_engine(cfg: dict):
    name = cfg["decision"]["engine"]
    if name == "trend_reversal":
        return TrendReversalEngine()
    # "ml_classifier": MLClassifierEngine,  # thêm ở giai đoạn 3 (xem docs/roadmap.md)
    # "rl_agent": RLAgentEngine,            # thêm ở giai đoạn 5
    raise ValueError(f"Decision engine '{name}' chưa được đăng ký trong main.py")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["backtest", "live"], default="backtest")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument(
        "--anchor-time",
        default=None,
        help=(
            "Mốc thời gian UTC để lấy dữ liệu, định dạng 'YYYY-MM-DD HH:MM:SS'. "
            "Bỏ trống = lấy realtime (mặc định). Ưu tiên hơn data.anchor_time "
            "trong config.yaml nếu cả hai cùng được khai báo."
        ),
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    anchor_time = parse_anchor_time(args.anchor_time) if args.anchor_time else None

    data_req = build_data_request(cfg, anchor_time_override=anchor_time)
    candles = clean_candles(fetch_from_request(data_req))

    # Tính toàn bộ feature cần thiết dựa theo config.features.indicators —
    # không còn hardcode ema(candles, 20)/rsi(candles, 14)... trong main.py.
    features = build_features(candles, cfg["features"]["indicators"])
    log_features(candles, features)  # -> logs/features.log
    engine = build_decision_engine(cfg)
    risk_manager = RiskManager(
        log_path=cfg.get("risk", {}).get("log_path", "logs/reversals.log")
    )

    if args.mode != "backtest":
        raise NotImplementedError("Live loop chưa implement — xem docs/roadmap.md giai đoạn 6.")

    results = run_backtest(candles, features, engine, risk_manager)

    reversal_count = sum(1 for r in results if r["signal"].is_reversal)
    log_path = cfg.get("risk", {}).get("log_path", "logs/reversals.log")
    anchor_note = f", mốc dữ liệu: {args.anchor_time}" if args.anchor_time else ", dữ liệu: realtime"
    print(
        f"Đã chạy backtest {len(results)} nến{anchor_note}, "
        f"phát hiện {reversal_count} điểm đảo chiều. Xem log tại {log_path}"
    )


if __name__ == "__main__":
    main()