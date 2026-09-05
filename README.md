# Trading Bot Framework

Khung code mô-đun cho hệ thống giao dịch tự động, cho phép thay thế lớp
"decision engine" (rule-based → ML → RL) mà không phải sửa các lớp còn lại.

## Cấu trúc thư mục

```
trading_bot/
├── docs/
│   ├── architecture.md      # Kiến trúc tổng thể, sơ đồ luồng dữ liệu
│   └── roadmap.md           # Lộ trình phát triển theo từng giai đoạn
├── config/
│   └── config.yaml          # Cấu hình chung (symbol, timeframe, risk limits...)
├── data/
│   ├── fetch.py             # Lấy dữ liệu giá thô từ sàn/API
│   └── pipeline.py          # Làm sạch, đồng bộ timeframe, ghép dữ liệu
├── features/
│   ├── indicators.py        # Tính chỉ báo kỹ thuật (MA, RSI, MACD, ATR...)
│   └── risk_labels.py       # Tính các nhãn phục vụ risk management (volatility...)
├── llm_filter/
│   └── regime_filter.py     # Module LLM độc lập, gắn nhãn regime thị trường
├── decision/
│   ├── base.py              # Interface chung mọi decision engine phải tuân theo
│   └── rule_based.py        # Cài đặt đầu tiên: rule-based (MA crossover...)
├── risk/
│   ├── position_sizing.py   # Tính khối lượng lệnh theo volatility (ATR-based)
│   └── risk_manager.py      # Stop-loss/take-profit động, giới hạn drawdown
├── execution/
│   └── logger_execution.py  # Lớp thực thi CHỈ GHI LOG (không gửi lệnh thật)
├── backtest/
│   ├── engine.py            # Backtest engine: chạy tuần tự, không leak dữ liệu tương lai
│   └── metrics.py           # Tính PnL, Sharpe, max drawdown, win rate
├── tests/                   # Unit test cho từng module
├── main.py                  # Điểm khởi chạy, nối các lớp lại với nhau
└── requirements.txt
```

## Nguyên tắc thiết kế

1. **Decision engine là một interface (`decision/base.py`), không phải một class cụ thể.**
   Mọi engine (rule-based, ML, RL) đều implement cùng một method `decide(state) -> Signal`.
   Nhờ vậy `main.py` không cần biết engine bên trong là gì.

2. **LLM filter là module tách biệt, một chiều.**
   Nó chỉ cung cấp nhãn regime cho decision engine tham khảo, không có quyền
   ghi đè risk management hay execution. Nếu LLM lỗi/trả sai định dạng,
   hệ thống chỉ mất một bộ lọc phụ, không sập toàn bộ pipeline.

3. **Execution layer hiện tại chỉ ghi log — không kết nối sàn thật.**
   Đây là lựa chọn có chủ đích để bạn kiểm chứng toàn bộ pipeline (data → feature →
   decision → risk → log lệnh) trước khi cắm vào API sàn thật. Khi sẵn sàng,
   chỉ cần viết thêm một class execution mới implement cùng interface —
   không phải sửa `decision/`, `risk/`, hay `backtest/`.

4. **Backtest engine dùng chung code với live loop.**
   `main.py` và `backtest/engine.py` gọi cùng một chuỗi
   `pipeline → features → decision → risk → execution`, khác nhau ở chỗ
   backtest chạy trên dữ liệu lịch sử theo từng nến một (tránh nhìn tương lai),
   còn live chạy theo thời gian thực.

## Bắt đầu

```bash
pip install -r requirements.txt
python main.py --mode backtest --config config/config.yaml
```

Xem chi tiết kiến trúc và lộ trình phát triển trong `docs/architecture.md` và `docs/roadmap.md`.
