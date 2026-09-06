"""
Điểm khởi chạy — nối tất cả các lớp lại với nhau theo config.yaml.

    python main.py --mode backtest --config config/config.yaml
"""

import argparse
import yaml

from data.fetch import fetch_historical
from data.pipeline import clean_candles
from features.indicators import ema, atr, rsi, macd
from decision.rule_based import EmaCrossoverEngine
from decision.micro_trend_rsi import MicroTrendRsiEngine
from risk.risk_manager import RiskManager
from execution.logger_execution import LoggerExecution
from backtest.engine import run_backtest
from backtest.metrics import max_drawdown_pct, win_rate


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_decision_engine(cfg: dict):
    name = cfg["decision"]["engine"]
    if name == "rule_based":
        return EmaCrossoverEngine()
    if name == "micro_trend_rsi":
        opts = cfg["decision"].get("micro_trend_rsi", {})
        return MicroTrendRsiEngine(
            require_macd_confirmation=opts.get("require_macd_confirmation", False)
        )
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

    ema_20 = ema(candles, 20)
    ema_50 = ema(candles, 50)
    atr_14 = atr(candles, 14)

    engine_name = cfg["decision"]["engine"]
    engine = build_decision_engine(cfg)
    risk_manager = RiskManager(
        capital=cfg["backtest"]["initial_capital"],
        risk_per_trade_pct=cfg["risk"]["risk_per_trade_pct"],
        atr_multiplier_sl=cfg["risk"]["atr_multiplier_sl"],
        max_drawdown_pct=cfg["risk"]["max_drawdown_pct"],
    )
    execution = LoggerExecution(log_path=cfg["execution"]["log_path"])

    if args.mode != "backtest":
        raise NotImplementedError("Live loop chưa implement — xem docs/roadmap.md giai đoạn 6.")

    if engine_name == "micro_trend_rsi":
        opts = cfg["decision"].get("micro_trend_rsi", {})
        ema_fast = ema(candles, opts.get("ema_fast_period", 9))
        ema_mid = ema(candles, opts.get("ema_mid_period", 21))
        rsi_fast = rsi(candles, opts.get("rsi_fast_period", 7))
        _, _, macd_hist = macd(
            candles,
            fast=opts.get("macd_fast", 5),
            slow=opts.get("macd_slow", 13),
            signal=opts.get("macd_signal", 6),
        )
        results = run_backtest(
            candles, ema_20, ema_50, atr_14, engine, risk_manager, execution,
            ema_fast_series=ema_fast,
            ema_mid_series=ema_mid,
            rsi_fast_series=rsi_fast,
            macd_hist_series=macd_hist,
        )
    else:
        results = run_backtest(
            candles, ema_20, ema_50, atr_14, engine, risk_manager, execution,
        )

    print(f"Đã chạy backtest {len(results)} nến. Xem log lệnh tại {cfg['execution']['log_path']}")


if __name__ == "__main__":
    main()
