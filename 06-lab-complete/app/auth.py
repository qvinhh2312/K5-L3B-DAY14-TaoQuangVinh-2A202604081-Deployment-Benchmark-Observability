"""
API Key authentication.

Client gửi header X-API-Key; giá trị phải trùng biến môi trường AGENT_API_KEY.
Thiếu key, sai key hoặc server chưa cấu hình key đều trả 401.
"""
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings

# auto_error=False: thiếu header thì tự trả 401 ở dưới, thay vì mã mặc định của FastAPI
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """Dependency cho FastAPI. Trả về key hợp lệ để dùng làm định danh khi rate limit."""
    expected = settings.agent_api_key
    # compare_digest: thời gian so sánh không phụ thuộc vị trí ký tự sai đầu tiên
    if (
        not expected
        or not api_key
        or not secrets.compare_digest(api_key.encode(), expected.encode())
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
    return api_key
