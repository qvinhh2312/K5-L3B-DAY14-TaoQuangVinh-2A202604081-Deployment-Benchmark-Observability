"""
Cost guard: giới hạn tổng chi phí LLM mỗi ngày, cộng dồn trong Redis.

Mỗi ngày (UTC) một key, nên ngân sách tự về 0 khi sang ngày mới.
"""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

# Giá USD / 1K tokens (tham khảo gpt-4o-mini)
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

KEY_TTL_SECONDS = 2 * 24 * 3600  # giữ thêm một ngày để còn tra cứu rồi tự xoá


def _today_key() -> str:
    return f"cost:{datetime.now(timezone.utc):%Y-%m-%d}"


def estimate_tokens(text: str) -> int:
    """Mock LLM không trả số token nên ước lượng khoảng 4 ký tự một token."""
    return max(1, len(text) // 4)


def check_budget() -> None:
    """Gọi TRƯỚC khi gọi LLM: đã tiêu hết ngân sách ngày thì raise HTTP 402."""
    spent = float(r.get(_today_key()) or 0)
    if spent >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    """Gọi SAU khi gọi LLM: cộng chi phí của request vào tổng, trả về chi phí đó."""
    cost = (
        input_tokens / 1000 * PRICE_INPUT_PER_1K
        + output_tokens / 1000 * PRICE_OUTPUT_PER_1K
    )
    key = _today_key()
    pipe = r.pipeline()
    pipe.incrbyfloat(key, cost)  # cộng nguyên tử trong Redis, không đọc rồi ghi đè
    pipe.expire(key, KEY_TTL_SECONDS)
    pipe.execute()
    return cost
