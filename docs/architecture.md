# Kiến trúc tổng thể

## Luồng dữ liệu

```
data/fetch.py
      │  (giá thô, tin tức)
      ▼
data/pipeline.py
      │  (dữ liệu đã làm sạch, đồng bộ timeframe)
      ▼
features/indicators.py + features/risk_labels.py
      │  (state: chỉ báo kỹ thuật, ATR, volatility)
      ▼                              ▲
decision/base.py (interface)   llm_filter/regime_filter.py
      │  (Signal: BUY/SELL/HOLD)     │  (nhãn regime, một chiều)
      ▼
risk/position_sizing.py + risk/risk_manager.py
      │  (Order: size, stop-loss, take-profit)
      ▼
execution/logger_execution.py
      │  (log lệnh, không gửi lệnh thật)
      ▼
backtest/engine.py + backtest/metrics.py
      (PnL, Sharpe, drawdown — dùng để đánh giá, feedback ngược lại decision engine)
```

## Vì sao tách lớp như vậy

| Lớp | Trách nhiệm duy nhất | KHÔNG làm gì |
|---|---|---|
| `data/` | Lấy và làm sạch dữ liệu | Không tính chỉ báo, không quyết định |
| `features/` | Biến dữ liệu thô thành state có ý nghĩa | Không biết gì về lệnh hay rủi ro |
| `llm_filter/` | Gắn nhãn regime thị trường (phụ trợ) | Không tự ra quyết định vào/thoát lệnh |
| `decision/` | Sinh tín hiệu BUY/SELL/HOLD | Không tính khối lượng, không quản lý rủi ro |
| `risk/` | Chuyển tín hiệu thành lệnh cụ thể (size, SL/TP) | Không biết logic vào lệnh là gì |
| `execution/` | Ghi log lệnh (giai đoạn hiện tại) | Không gửi lệnh thật ra sàn |
| `backtest/` | Đo lường hiệu quả toàn hệ thống | Không thay đổi logic của các lớp khác |

Mỗi lớp chỉ giao tiếp với lớp liền kề qua một cấu trúc dữ liệu rõ ràng
(`MarketState`, `Signal`, `Order`) được định nghĩa trong `decision/base.py`
và `risk/risk_manager.py`. Nhờ vậy bạn có thể viết unit test cho từng lớp
độc lập, và thay bất kỳ lớp nào (ví dụ đổi rule-based sang ML) mà không
ảnh hưởng các lớp còn lại.

## Về execution layer chỉ ghi log

Ở giai đoạn hiện tại, `execution/logger_execution.py` không kết nối sàn —
nó nhận một `Order` từ `risk_manager` và chỉ:
1. Ghi log ra file/console (thời gian, symbol, hướng lệnh, size, SL/TP, lý do vào lệnh).
2. Trả về một `ExecutionResult` giả lập (fill giá đóng cửa nến hiện tại) để
   `backtest/engine.py` vẫn tính được PnL.

Khi sẵn sàng kết nối sàn thật, tạo thêm `execution/live_execution.py`
implement cùng interface (`class Execution: def send_order(order) -> ExecutionResult`)
— không cần sửa bất kỳ file nào khác.
