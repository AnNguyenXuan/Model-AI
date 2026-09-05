"""
Module LLM độc lập — gắn nhãn regime thị trường (Trending/Sideway/High-volatility).

QUY TẮC QUAN TRỌNG:
- Module này CHỈ được đọc, không được ghi vào risk/ hoặc execution/.
- Nếu LLM lỗi hoặc trả JSON không hợp lệ, `get_regime()` phải trả về "unknown"
  thay vì raise exception làm sập toàn bộ pipeline.
- Luôn validate nhãn trả về so với một baseline thống kê trước khi tin dùng
  trong production (xem docs/roadmap.md, giai đoạn 4).
"""

import json
from dataclasses import dataclass
from typing import Literal

Regime = Literal["trending", "sideways", "high_volatility", "unknown"]


@dataclass
class RegimeResult:
    regime: Regime
    raw_response: str


def get_regime(market_summary: dict) -> RegimeResult:
    """
    Gửi tóm tắt thị trường (chỉ báo + tin tức) cho LLM, ép trả JSON,
    và parse an toàn.

    TODO: thay bằng lời gọi thật tới Ollama/API nội bộ với
    response_format ép JSON. Giữ nguyên hợp đồng: luôn trả về RegimeResult,
    không bao giờ raise ra ngoài.
    """
    try:
        raw = _call_llm(market_summary)  # TODO: implement
        parsed = json.loads(raw)
        regime = parsed.get("regime", "unknown")
        if regime not in ("trending", "sideways", "high_volatility"):
            regime = "unknown"
        return RegimeResult(regime=regime, raw_response=raw)
    except Exception:
        # Không bao giờ để lỗi LLM làm crash pipeline chính.
        return RegimeResult(regime="unknown", raw_response="")


def _call_llm(market_summary: dict) -> str:
    raise NotImplementedError("Cắm lời gọi tới LLM local/API tại đây, ép JSON output.")
