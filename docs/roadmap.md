# Lộ trình phát triển

## Giai đoạn 1 — Nền móng (đang ở đây)
- [ ] Hoàn thiện `data/pipeline.py`: lấy dữ liệu OHLCV, đảm bảo không có gap, không leak nến tương lai.
- [ ] Hoàn thiện `backtest/engine.py`: chạy tuần tự từng nến, kiểm chứng bằng vài case tay (biết trước PnL đúng).
- [ ] `decision/rule_based.py`: MA crossover hoặc RSI đơn giản, chỉ để kiểm thử toàn bộ pipeline chạy được đầu-cuối.
- [ ] `execution/logger_execution.py`: log đầy đủ mọi lệnh giả lập.

**Tiêu chí hoàn thành:** chạy `python main.py --mode backtest` cho ra file log lệnh
và báo cáo PnL/Sharpe/drawdown khớp với tính tay trên một bộ dữ liệu nhỏ.

## Giai đoạn 2 — Risk management
- [ ] `risk/position_sizing.py`: sizing theo ATR thay vì % vốn cố định.
- [ ] `risk/risk_manager.py`: stop-loss động, giới hạn drawdown tổng (ví dụ dừng bot nếu drawdown > X%).

## Giai đoạn 3 — ML cổ điển
- [ ] Thêm `decision/ml_classifier.py` implement cùng interface `decision/base.py`.
- [ ] Dùng dữ liệu từ giai đoạn 1 để train XGBoost/LightGBM dự đoán xác suất tăng/giảm.
- [ ] So sánh kết quả backtest giữa `rule_based` và `ml_classifier` bằng cùng một `backtest/engine.py`.

## Giai đoạn 4 — LLM regime filter
- [ ] Hoàn thiện `llm_filter/regime_filter.py`: gọi LLM local (Ollama), ép JSON output.
- [ ] Validate: so sánh nhãn regime của LLM với nhãn thống kê (ví dụ volatility rolling window) trên dữ liệu lịch sử trước khi tin dùng.
- [ ] Tích hợp như một filter phụ trợ trong `decision/`, không thay đổi risk/execution.

## Giai đoạn 5 — RL (tuỳ chọn, sau cùng)
- [ ] Thêm `decision/rl_agent.py` implement cùng interface.
- [ ] Dùng lại toàn bộ `data/`, `features/`, `risk/`, `backtest/` đã kiểm chứng ở các giai đoạn trước.

## Giai đoạn 6 — Live (chỉ khi paper trading ổn định đủ lâu)
- [ ] Thêm `execution/live_execution.py` kết nối API sàn thật.
- [ ] Chạy song song log-only và live trên tài khoản demo trước khi dùng vốn thật.
