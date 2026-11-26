"""
Rate limiting: sliding window 60 giây cho mỗi API key, state nằm trong Redis.

Mỗi key là một sorted set: member là một request, score là thời điểm gọi.
"""
import hashlib
import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

WINDOW_SECONDS = 60

# Redis chạy cả script như một thao tác duy nhất, nên nhiều worker / instance
# không thể cùng đếm "còn chỗ" rồi cùng thêm vào, vượt quá giới hạn.
# KEYS[1] = sorted set;  ARGV = now, window, limit, member
# Trả về 0 nếu được phép, ngược lại là số giây phải chờ.
_sliding_window = r.register_script("""
local now, window, limit = tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
if redis.call('ZCARD', KEYS[1]) >= limit then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    if oldest[2] then
        return math.max(1, math.ceil(tonumber(oldest[2]) + window - now))
    end
    return window
end
redis.call('ZADD', KEYS[1], now, ARGV[4])
redis.call('EXPIRE', KEYS[1], window)
return 0
""")


def _redis_key(api_key: str) -> str:
    # Băm key để secret không xuất hiện trong Redis
    return "ratelimit:" + hashlib.sha256(api_key.encode()).hexdigest()[:16]


def check_rate_limit(key: str) -> None:
    """Ghi nhận một request của key này; vượt giới hạn thì raise HTTP 429."""
    now = time.time()
    retry_after = _sliding_window(
        keys=[_redis_key(key)],
        args=[now, WINDOW_SECONDS, settings.rate_limit_per_minute, f"{now}:{uuid.uuid4().hex}"],
    )
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} requests per minute",
            headers={"Retry-After": str(retry_after)},
        )
