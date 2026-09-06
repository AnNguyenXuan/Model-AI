"""
Điểm khởi chạy — nối tất cả các lớp lại với nhau theo config.yaml.

    python main.py --mode backtest --config config/config.yaml

Giai đoạn hiện tại: pipeline chỉ sinh TÍN HIỆU đảo chiều (BUY/SELL/HOLD),
CHƯA tính size/SL/TP (xem risk/risk_manager.py). Xem docs/roadmap.md giai
đoạn 2 khi cần thêm quản lý vốn.
"""

import argparse
import yaml

from data.fetch import fetch_historical
from data.pipeline import clean_candles
from features.registry import build_features
from decision.trend_reversal import TrendReversalEngine
from risk.risk_manager import RiskManager
from backtest.engine import run_backtest


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    args = parser.parse_args()

    cfg = load_config(args.config)

    candles = clean_candles(
        fetch_historical(cfg["symbol"], cfg["timeframe"], cfg["data"]["lookback_bars"])
    )

    # Tính toàn bộ feature cần thiết dựa theo config.features.indicators —
    # không còn hardcode ema(candles, 20)/rsi(candles, 14)... trong main.py.
    features = build_features(candles, cfg["features"]["indicators"])

    engine = build_decision_engine(cfg)
    risk_manager = RiskManager(
        log_path=cfg.get("risk", {}).get("log_path", "logs/reversals.log")
    )

    if args.mode != "backtest":
        raise NotImplementedError("Live loop chưa implement — xem docs/roadmap.md giai đoạn 6.")

    results = run_backtest(candles, features, engine, risk_manager)

    reversal_count = sum(1 for r in results if r["signal"].is_reversal)
    log_path = cfg.get("risk", {}).get("log_path", "logs/reversals.log")
    print(
        f"Đã chạy backtest {len(results)} nến, phát hiện {reversal_count} điểm đảo chiều. "
        f"Xem log tại {log_path}"
    )


if __name__ == "__main__":
    main()
