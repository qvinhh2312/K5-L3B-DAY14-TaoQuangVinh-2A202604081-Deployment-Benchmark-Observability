"""
Production AI Agent — Part 6 Final Project (bản khung)

Hoàn thành các TODO để đạt đủ 12 tiêu chí trong README.md, rồi kiểm tra:
    python check_production_ready.py

Bản khung này chạy được (uvicorn app.main:app) nhưng chưa đạt tiêu chí nào.
"""
import logging
import time

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.logging_config import setup_logging
from utils.mock_llm import ask as llm_ask

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Production AI Agent")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Mỗi request một dòng log. Không ghi header, query hay body để tránh lộ secret."""
    start = time.perf_counter()
    status = 500  # giữ nguyên nếu handler ném exception
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        logger.info("request", extra={"fields": {
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "ms": round((time.perf_counter() - start) * 1000, 1),
        }})


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.get("/health")
def health():
    """Liveness: process còn chạy thì trả 200, không phụ thuộc Redis."""
    return {"status": "ok"}


# TODO (tiêu chí 5): GET /ready  — readiness: 200 khi sẵn sàng, 503 khi Redis không kết nối được


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    # TODO (tiêu chí 7): check_rate_limit(...) → 429 khi vượt giới hạn
    # TODO (tiêu chí 8): check_budget() trước khi gọi LLM, record_cost(...) sau khi gọi → 402 khi hết budget
    answer = llm_ask(body.question)
    return {"question": body.question, "answer": answer}


# TODO (tiêu chí 11 — Graceful shutdown):
#   Khi nhận SIGTERM: ngừng nhận request mới, xử lý xong request đang chạy rồi thoát (exit code 0).
#   Gợi ý: dùng lifespan của FastAPI để dọn dẹp. Nếu tự đăng ký signal handler cho SIGTERM thì
#   phải gọi lại handler cũ của uvicorn, nếu không process sẽ không bao giờ tắt.
