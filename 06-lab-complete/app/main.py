"""
Production AI Agent — Part 6 Final Project.

Luồng của POST /ask: API key → rate limit → ngân sách → LLM → ghi chi phí.
State (rate limit, chi phí) nằm trong Redis, process không giữ state.

Chạy:  uvicorn app.main:app
Kiểm tra:  python check_production_ready.py
"""
import logging
import time
from contextlib import asynccontextmanager

import redis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, estimate_tokens, record_cost
from app.logging_config import setup_logging
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Graceful shutdown. Khi nhận SIGTERM, uvicorn ngừng nhận kết nối mới, chờ các
    request đang chạy xong rồi mới chạy phần sau `yield`. Không tự đăng ký signal
    handler để không ghi đè handler của uvicorn.
    """
    logger.info("startup", extra={"fields": {"environment": settings.environment}})
    yield
    r.close()  # đóng kết nối Redis sau khi request cuối cùng đã xong
    logger.info("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Mỗi request một dòng log. Không ghi header, query hay body để tránh lộ secret."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # Lỗi không lường trước: stack trace chỉ ghi vào log, client nhận thông báo chung
        logger.exception("unhandled_error", extra={"fields": {"path": request.url.path}})
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    logger.info("request", extra={"fields": {
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ms": round((time.perf_counter() - start) * 1000, 1),
    }})
    return response


@app.exception_handler(redis.RedisError)
def redis_unavailable(request: Request, exc: redis.RedisError):
    """Mất Redis thì không kiểm tra được rate limit và ngân sách: từ chối bằng 503."""
    logger.error("redis_error", extra={"fields": {"error": type(exc).__name__}})
    return JSONResponse(status_code=503, content={"detail": "Service temporarily unavailable"})


class AskRequest(BaseModel):
    # Cắt khoảng trắng trước khi kiểm tra, nên câu hỏi toàn dấu cách bị từ chối (422)
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(..., min_length=1, max_length=2000)


@app.get("/health")
def health():
    """Liveness: process còn chạy thì trả 200, không phụ thuộc Redis."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness: chỉ nhận traffic khi kết nối được Redis."""
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis is not available")
    return {"status": "ready"}


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    check_budget()
    answer = llm_ask(body.question)
    input_tokens = estimate_tokens(body.question)
    output_tokens = estimate_tokens(answer)
    cost = record_cost(input_tokens, output_tokens)
    logger.info("llm_call", extra={"fields": {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 8),
    }})
    return {"question": body.question, "answer": answer}
