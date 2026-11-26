"""
Kết nối Redis dùng chung cho rate limiter và cost guard.

from_url chỉ tạo client, chưa kết nối: app khởi động được khi Redis chưa sẵn sàng.
"""
import redis

from app.config import settings

r = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,       # trả về str thay vì bytes
    socket_connect_timeout=2,    # Redis không tới được thì báo lỗi sau 2 giây, không treo request
    socket_timeout=2,
)


def redis_healthy() -> bool:
    """Dùng cho GET /ready: Redis trả lời PING thì True."""
    try:
        return bool(r.ping())
    except redis.RedisError:
        return False
