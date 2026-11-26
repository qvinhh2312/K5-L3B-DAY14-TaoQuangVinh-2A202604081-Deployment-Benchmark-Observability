# ============================================================
# Production AI Agent — multi-stage, non-root
# ============================================================

# ── Stage 1: builder — chỉ để cài dependencies ──────────────
FROM python:3.11-slim AS builder

WORKDIR /build
# Copy requirements trước code: sửa code không làm mất cache của layer pip install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime — image đem đi chạy ────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# User hệ thống không đặc quyền
RUN groupadd --system agent && useradd --system --gid agent --no-create-home agent

WORKDIR /app

# Chỉ lấy thư viện đã cài từ builder
COPY --from=builder /install /usr/local
# Chỉ copy code cần để chạy. File thuộc root nên user agent đọc được nhưng không sửa được.
COPY app/ ./app/
COPY utils/ ./utils/

USER agent

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT', '8000'), timeout=3)" || exit 1

# sh -c để đọc được ${PORT}; exec để uvicorn thay thế sh làm PID 1 và nhận SIGTERM.
# --timeout-graceful-shutdown 8: chờ request đang chạy, vẫn kịp trước hạn 10 giây của docker stop.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --timeout-graceful-shutdown 8 --no-access-log"]
