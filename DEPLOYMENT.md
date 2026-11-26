# Deployment Information

## Public URL

https://agent-production-8adbaa12.up.railway.app

## Platform

Railway, gồm 2 service:

| Service | Vai trò |
|---|---|
| `agent` | Agent trong `06-lab-complete/`, build bằng `Dockerfile` |
| `Redis` | Lưu trạng thái rate limit và chi phí, có volume `redis-volume` |

## Cách deploy

Chạy trong `06-lab-complete/`:

```powershell
railway login
railway init
railway add --database redis
railway add --service agent
railway variable set "AGENT_API_KEY=<key tạo bằng openssl rand -hex 32>" --service agent
railway variable set 'REDIS_URL=${{Redis.REDIS_URL}}' --service agent
railway variable set ENVIRONMENT=production --service agent
railway up . --path-as-root --service agent
railway domain --service agent
```

## Test Commands

```bash
BASE=https://agent-production-8adbaa12.up.railway.app
# AGENT_API_KEY: giá trị đã đặt trên Railway, không ghi vào repo

curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"     # 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"      # 200
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'                    # 401
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}'                                                        # 200
```

Kết quả chạy ngày 26/11/2026: `200`, `200`, `401`, `200` (xem `screenshots/test.png`).

## Environment Variables Set

| Biến | Nguồn |
|---|---|
| `AGENT_API_KEY` | Đặt trên Railway |
| `REDIS_URL` | Tham chiếu `${{Redis.REDIS_URL}}` tới service Redis |
| `ENVIRONMENT` | `production` |
| `PORT` | Railway tự cấp; log cho thấy agent nghe cổng 8080 |

`RATE_LIMIT_PER_MINUTE` và `DAILY_BUDGET_USD` không đặt, dùng mặc định trong `app/config.py` (10 request/phút, 1.0 USD/ngày).

## Ghi chú về `railway.toml`

Khi deploy, Railway CLI cảnh báo Config as Code (`railway.toml`) đã deprecated, file hiện có vẫn hoạt động đến 01/12/2026. Sau mốc đó cần chuyển sang Infrastructure as Code (`.railway/railway.ts`).

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
