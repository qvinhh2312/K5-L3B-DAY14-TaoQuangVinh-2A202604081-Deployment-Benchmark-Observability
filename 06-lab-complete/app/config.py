"""
Config — 12-Factor: mọi cấu hình đọc từ biến môi trường.

Giá trị mặc định chỉ để chạy ở máy local. Secret (AGENT_API_KEY) không có
mặc định: để trống thì không request nào được chấp nhận.
"""
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""))
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    )
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )
    daily_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("DAILY_BUDGET_USD", "1.0"))
    )


settings = Settings()
