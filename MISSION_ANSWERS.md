# Day 14 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

File xét: `01-localhost-vs-production/develop/app.py`.

| # | Anti-pattern | Dòng | Hậu quả khi lên production |
|---|---|---|---|
| 1 | Hardcode API key và chuỗi kết nối database (kèm mật khẩu) | 17–18 | Ai đọc được repo hoặc lịch sử git là lấy được; đổi key phải sửa code |
| 2 | In API key ra log | 34 | Người xem log lấy được key (thấy trong log ở Exercise 1.2) |
| 3 | `DEBUG`, `MAX_TOKENS` cố định trong code | 21–22 | Không đổi được cấu hình theo môi trường nếu không sửa code |
| 4 | Dùng `print` thay cho logging | 33, 38 | Không có mức log, thời gian, định dạng để lọc và tìm kiếm |
| 5 | Không có health check | 42–43 | Nền tảng không biết app còn sống để restart (`/health` trả 404) |
| 6 | Bind `localhost` | 51 | Trong container, request từ bên ngoài không tới được app |
| 7 | Cổng cố định 8000 | 52 | Không nghe được cổng do Railway/Render cấp qua biến `PORT` |
| 8 | `reload=True` | 53 | Chạy thêm tiến trình theo dõi file, tốn tài nguyên, không ổn định cho production |
| 9 | Nhận `question` qua query string | 31 | Nội dung người dùng bị ghi vào access log (`POST /ask?question=Hello`) |

### Exercise 1.2: Kết quả chạy bản develop

Chạy `python app.py` trong `01-localhost-vs-production/develop/` (WSL2 Ubuntu 24.04), gửi request từ terminal thứ hai.

Request 1 và 2 được chạy lại lúc 08:20 để chép đủ body. Request 3 và log server bên dưới là của lần chạy đầu (08:13), nên câu trả lời của mock LLM (chọn ngẫu nhiên) khác nhau.

**Request 1: hỏi agent, `question` truyền qua query**

```text
$ curl -i -X POST "http://localhost:8000/ask?question=Hello"; echo
HTTP/1.1 200 OK
date: Thu, 26 Nov 2026 08:20:13 GMT
server: uvicorn
content-length: 126
content-type: application/json

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

**Request 2: health check**

```text
$ curl -i http://localhost:8000/health; echo
HTTP/1.1 404 Not Found
date: Thu, 26 Nov 2026 08:20:23 GMT
server: uvicorn
content-length: 22
content-type: application/json

{"detail":"Not Found"}
```

**Request 3: gửi `question` trong body JSON**

```text
$ curl -i -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"Hello"}'
HTTP/1.1 422 Unprocessable Entity
date: Thu, 26 Nov 2026 08:13:59 GMT
server: uvicorn
content-length: 94
content-type: application/json

{"detail":[{"type":"missing","loc":["query","question"],"msg":"Field required","input":null}]}
```

**Log server (API key đã che)**

```text
Starting agent on localhost:8000...
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [1861] using WatchFiles
INFO:     Started server process [1863]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
[DEBUG] Got question: Hello
[DEBUG] Using key: sk-***
[DEBUG] Response: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.
INFO:     127.0.0.1:55674 - "POST /ask?question=Hello HTTP/1.1" 200 OK
INFO:     127.0.0.1:48806 - "GET /health HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:48816 - "POST /ask HTTP/1.1" 422 Unprocessable Entity
^CINFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1863]
INFO:     Stopping reloader process [1861]
```

**Nhận xét**

- App chạy được và trả 200 trên máy local, nhưng in cả API key ra log: ai đọc được log là lấy được key.
- Không có `/health` (404) nên nền tảng cloud không kiểm tra được app còn sống để restart. App cũng đang bind `localhost`, cổng 8000 cố định và bật reload, chưa phù hợp để deploy.
- `/ask` nhận `question` qua query, nên gửi body JSON bị 422.

### Exercise 1.3: Comparison table

Số dòng: `app.py` và `config.py` trong `01-localhost-vs-production/production/`.

| Feature | Develop | Production | Tại sao quan trọng |
|---|---|---|---|
| Config | Cố định trong code | Đọc từ biến môi trường, gom vào `Settings` (`config.py` 14–35) | Cùng một code chạy được ở dev, staging, production |
| Secrets | Hardcode và in ra log | `os.getenv` (`config.py` 27, 32), không log key; thiếu `AGENT_API_KEY` khi `ENVIRONMENT=production` thì dừng ngay (`config.py` 42–43) | Tránh lộ key; phát hiện thiếu cấu hình lúc khởi động |
| Host / Port | `localhost:8000` cố định | `0.0.0.0` và `PORT` từ môi trường (`config.py` 17–18, `app.py` 196–197) | Nhận được request từ ngoài container, đúng cổng nền tảng cấp |
| Reload | Luôn bật | Chỉ bật khi `DEBUG=true` (`app.py` 198) | Production không tự nạp lại code |
| Health check | Không có | `/health` (135–149), `/ready` (152–161) | `/health` để quyết định restart; `/ready` để quyết định có gửi traffic không |
| Logging | `print` | `logging` theo định dạng giống JSON, không log secret (28–31, 111–122) | Lọc, tìm kiếm được; xem thêm lỗi bên dưới |
| Input | Query string, không kiểm tra | JSON body, thiếu `question` thì 422 (104–108) | Câu hỏi không nằm trong URL của access log |
| Shutdown | Chỉ có cơ chế mặc định của uvicorn | Thêm `lifespan` đặt `is_ready=False`, ghi log khi tắt (39–67) và handler SIGTERM (180–189) | Chỗ để ngừng nhận traffic và đóng kết nối trước khi thoát |

**Kết quả chạy bản production**

Chạy `python app.py` (không đặt `OPENAI_API_KEY`), output curl đã lược bớt vài header:

```text
$ curl -i http://localhost:8000/health; echo
HTTP/1.1 200 OK
date: Thu, 26 Nov 2026 08:30:36 GMT

{"status":"ok","uptime_seconds":95.0,"version":"1.0.0","environment":"development","timestamp":"2026-11-26T08:30:36.917230+00:00"}

$ curl -i http://localhost:8000/ready; echo
HTTP/1.1 200 OK
date: Thu, 26 Nov 2026 08:30:44 GMT

{"ready":true}

$ curl -i -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"Hello"}'; echo
HTTP/1.1 200 OK
date: Thu, 26 Nov 2026 08:30:51 GMT

{"question":"Hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","model":"gpt-4o-mini"}
```

Log server của lần chạy này chỉ có cảnh báo `WARNING:root:OPENAI_API_KEY not set — using mock LLM` và log của uvicorn, không có dòng log nào của app.

**Thí nghiệm: đặt key giả để hết cảnh báo, tắt bằng SIGTERM**

```text
$ OPENAI_API_KEY=fake-key python app.py
{"time":"2026-11-26 08:34:14,468","level":"INFO","msg":"Starting AI Agent on 0.0.0.0:8000"}
INFO:     Started server process [2293]
INFO:     Waiting for application startup.
{"time":"2026-11-26 08:34:14,484","level":"INFO","msg":"{"event": "startup", "app": "AI Agent", "version": "1.0.0", "env": "development", "port": 8000}"}
{"time":"2026-11-26 08:34:14,584","level":"INFO","msg":"Agent is ready to serve requests"}
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
{"time":"2026-11-26 08:34:25,446","level":"INFO","msg":"{"event": "agent_request", "question_length": 5, "client_ip": "127.0.0.1"}"}
{"time":"2026-11-26 08:34:25,573","level":"INFO","msg":"{"event": "agent_response", "response_length": 66}"}
INFO:     127.0.0.1:33318 - "POST /ask HTTP/1.1" 200 OK
INFO:     Shutting down
INFO:     Waiting for application shutdown.
{"time":"2026-11-26 08:34:25,775","level":"INFO","msg":"Agent shutting down gracefully — finishing in-flight requests..."}
{"time":"2026-11-26 08:34:25,876","level":"INFO","msg":"Shutdown complete"}
INFO:     Application shutdown complete.
INFO:     Finished server process [2293]
{"time":"2026-11-26 08:34:25,876","level":"INFO","msg":"Received SIGTERM — initiating graceful shutdown"}
```

**Những lỗi còn lại của bản production**

1. **Mất log của app khi thiếu `OPENAI_API_KEY`.** `config.py` dòng 45 gọi `logging.warning()` lúc import, tự cấu hình logging ở mức `WARNING`. Do đó `basicConfig` trong `app.py` (28–31) không còn tác dụng và các `logger.info` bị bỏ.
2. **Log không phải JSON hợp lệ.** Khi `msg` chứa kết quả `json.dumps`, dấu ngoặc kép bên trong không được escape (xem dòng `agent_request`). Cách sửa: viết `logging.Formatter` dùng `json.dumps` cho cả dòng log.
3. **Handler SIGTERM không phải thứ khởi động việc tắt.** Dòng `Received SIGTERM` in sau `Shutdown complete`: uvicorn nhận tín hiệu, tắt app xong rồi mới gọi lại handler này.
4. **`.env` không được nạp.** Code không gọi `load_dotenv`, nên `cp .env.example .env` không có tác dụng khi chạy `python app.py`.
5. **`/ask` chưa xác thực**, dù `config.py` đã đọc `AGENT_API_KEY`.

Thí nghiệm gửi SIGTERM sau khi request đã trả về, nên **chưa kiểm chứng** việc giữ request đang chạy. Cả hai bản đều tắt gọn qua uvicorn (bản develop mới thử bằng Ctrl+C), nên khác biệt quan sát được là bản production có thêm bước dọn dẹp và log, không phải "tắt đột ngột" so với "tắt êm".

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

File xét: `02-docker/develop/Dockerfile`.

1. **Base image:** `python:3.11` (dòng 8), bản Python đầy đủ trên Debian, kèm nhiều công cụ build nên rất lớn.
2. **Working directory:** `/app` (dòng 11). Các lệnh `COPY`, `RUN`, `CMD` phía sau chạy tương đối so với thư mục này.
3. **Vì sao copy `requirements.txt` trước** (dòng 14–17): Docker cache theo layer. Khi chỉ sửa code, layer `requirements.txt` và `pip install` không đổi nên được dùng lại, không phải tải lại thư viện. Nếu copy toàn bộ code trước, mỗi lần sửa code là `pip install` chạy lại.
4. **`CMD` khác `ENTRYPOINT`:** `CMD` là lệnh mặc định, bị thay khi truyền lệnh sau tên image trong `docker run`. `ENTRYPOINT` là chương trình cố định, tham số truyền vào được nối phía sau (muốn thay phải dùng `--entrypoint`). Hai lệnh có thể kết hợp: `ENTRYPOINT` là chương trình, `CMD` là tham số mặc định. File này dùng `CMD ["python", "app.py"]` (dòng 30) ở dạng exec, nên Python là PID 1 và nhận được tín hiệu dừng.

Build từ gốc repo nên các đường dẫn `COPY` tính từ gốc, và Docker dùng `.dockerignore` ở gốc repo.

### Exercise 2.2: Build và run

```text
$ docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
$ docker run -d --rm --name agent-dev -p 8000:8000 my-agent:develop
$ curl -i -X POST "http://localhost:8000/ask?question=What%20is%20Docker"; echo
HTTP/1.1 200 OK
date: Thu, 26 Nov 2026 08:46:43 GMT
server: uvicorn
content-length: 103
content-type: application/json

{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

### Exercise 2.3: Image size comparison

```text
$ docker images | grep my-agent
                                       DISK USAGE   CONTENT SIZE
my-agent:advanced     ab708d20bb9e          240MB         57.4MB
my-agent:develop      1e4def837a25         1.67GB          426MB
```

| Image | Disk usage | Content size (nén) |
|---|---|---|
| Develop | 1670 MB | 426 MB |
| Production | 240 MB | 57.4 MB |
| Chênh lệch | giảm 85,6% | giảm 86,5% |

**Hai stage trong `02-docker/production/Dockerfile`**

- **Stage 1 `builder`** (dòng 16–29): từ `python:3.11-slim`, cài `gcc`, `libpq-dev`, rồi `pip install --user` vào `/root/.local`.
- **Stage 2 `runtime`** (dòng 36–72): bắt đầu lại từ `python:3.11-slim` sạch, tạo user `appuser`, chỉ copy thư viện đã cài và code, chạy non-root, có `HEALTHCHECK`, uvicorn 2 worker.

**Vì sao image nhỏ hơn** (theo `docker history`)

| Thành phần | Develop | Production |
|---|---|---|
| Layer của base image (các layer chính) | 696 MB, 202 MB, 134 MB, 70.6 MB, 65 MB, 19.8 MB | 87.7 MB, 48.9 MB, 4.93 MB |
| Thư viện Python | 53.3 MB (`pip install`) | 40.8 MB (`COPY --from=builder`) |

- Phần giảm lớn nhất đến từ việc đổi base image `python:3.11` sang `python:3.11-slim`.
- Multi-stage giữ `gcc`, `libpq-dev` ở stage `builder`: `docker history` của image production không có layer nào cài chúng. Image cuối vì vậy nhỏ hơn và ít công cụ có thể bị lợi dụng hơn.

### Exercise 2.4: Docker Compose stack

```text
Client
  │ http://localhost:80
  ▼
┌────────────────────── network "internal" (bridge) ──────────────────────┐
│  nginx :80  ──proxy──▶  agent :8000 (1 container, 2 uvicorn worker)     │
│                            ┊ depends_on, REDIS_URL, QDRANT_URL          │
│                            ┊                                            │
│                  redis :6379          qdrant :6333                      │
│                  (volume redis_data)  (volume qdrant_data)              │
└─────────────────────────────────────────────────────────────────────────┘
```

**Kết quả chạy**

```text
$ docker compose -p k5-day14-docker -f 02-docker/production/docker-compose.yml up -d --build
 ✔ Container k5-day14-docker-redis-1  Healthy
 ✔ Container k5-day14-docker-qdrant-1 Healthy
 ✔ Container k5-day14-docker-agent-1  Started
 ✔ Container k5-day14-docker-nginx-1  Started

$ docker compose -p k5-day14-docker -f 02-docker/production/docker-compose.yml ps
SERVICE   STATUS                            PORTS
agent     Up 2 seconds (health: starting)   8000/tcp
nginx     Up 2 seconds                      0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
qdrant    Up 13 seconds (healthy)           6333-6334/tcp
redis     Up 13 seconds (healthy)           6379/tcp
```

**Test qua Nginx** (output lược bớt vài header)

```text
$ curl -i http://localhost/health; echo
HTTP/1.1 200 OK
Server: nginx
X-Frame-Options: DENY
X-Content-Type-Options: nosniff

{"status":"ok","uptime_seconds":9.5,"version":"2.0.0","timestamp":"2026-11-26T08:49:48.676788"}

$ curl -i -X POST http://localhost/ask -H "Content-Type: application/json" -d '{"question":"Explain microservices"}'; echo
HTTP/1.1 200 OK
Server: nginx

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

**Log**

```text
agent-1  | INFO:     Started parent process [1]
agent-1  | INFO:     Started server process [9]
agent-1  | INFO:     Started server process [8]
agent-1  | {"time":"2026-11-26 08:49:53,618","level":"INFO","msg":"{"event": "request", "q_len": 21}"}
agent-1  | INFO:     172.20.0.5:56328 - "POST /ask HTTP/1.1" 200 OK
nginx-1  | 172.20.0.1 - - [26/Nov/2026:08:49:53 +0000] "POST /ask HTTP/1.1" 200 126 "-" "curl/8.5.0"
```

**Services và cách giao tiếp**

- 4 service được start: `agent`, `redis`, `qdrant`, `nginx`. `redis` và `qdrant` phải `healthy` thì `agent` mới start (`depends_on`).
- Các service gọi nhau bằng tên service qua DNS nội bộ của Docker trong network `internal`.
- Chỉ `nginx` mở cổng ra máy host. Request đi `client → nginx → agent`.
- Nginx giới hạn 10 request/giây mỗi IP cho `location /` (không áp dụng cho `/health`) và thêm security header.

**Chỗ cấu hình chưa khớp**

- Ghi chú đầu file compose nói agent có 2 replica, nhưng không có `replicas` nên chỉ chạy 1 container; 2 tiến trình trong log là 2 worker của uvicorn.
- Compose truyền `REDIS_URL`, `QDRANT_URL`, nhưng `main.py` không dùng Redis hay Qdrant.
- Cổng 443 được map nhưng `nginx.conf` chỉ `listen 80`, nên chưa có HTTPS.
- Dòng log `request` không phải JSON hợp lệ, cùng lỗi như ở Part 1.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** https://agent-production-8adbaa12.up.railway.app
- Deploy agent Part 6 (`06-lab-complete/`) kèm một service Redis. Chi tiết trong [DEPLOYMENT.md](DEPLOYMENT.md).
- Ảnh: [dashboard](screenshots/dashboard.png), [service đang chạy](screenshots/running.png), [kết quả test](screenshots/test.png).

| Request tới URL public | Mã HTTP |
|---|---|
| `GET /health` | 200 |
| `GET /ready` | 200 |
| `POST /ask` không có key | 401 |
| `POST /ask` có `X-API-Key` | 200 |

### Exercise 3.2: So sánh `railway.toml` với `render.yaml`

So sánh hai file trong `06-lab-complete/`. Chỉ deploy lên Railway; `render.yaml` chưa chạy thử trên Render.

| Tiêu chí | `railway.toml` | `render.yaml` |
|---|---|---|
| Định dạng | TOML | YAML |
| Phạm vi | Cấu hình build và deploy của **một** service | Blueprint khai báo **cả hạ tầng**: web service và Key Value (Redis) |
| Cách build | `builder = "DOCKERFILE"`, `dockerfilePath` | `runtime: docker`, `rootDir: 06-lab-complete` |
| Health check | `healthcheckPath`, `healthcheckTimeout` | `healthCheckPath` |
| Tạo Redis | Ngoài file: `railway add --database redis` | Trong file: service `type: keyvalue` |
| Nối agent với Redis | Biến `REDIS_URL=${{Redis.REDIS_URL}}` đặt bằng CLI | `fromService` lấy `connectionString` |
| Biến môi trường, secret | Đặt trên nền tảng, không nằm trong file | Khai báo trong `envVars`; secret dùng `generateValue: true` nên giá trị không nằm trong git |
| Region, gói | Không khai báo trong file | `region`, `plan` |
| Restart | `restartPolicyType`, `restartPolicyMaxRetries` | Không khai báo, do Render quản lý |

**Vì sao khác:** `railway.toml` chỉ mô tả cách build và chạy một service, còn tài nguyên và biến được quản lý trên project. Blueprint của Render theo hướng Infrastructure as Code: một file đủ để dựng lại toàn bộ hệ thống, đổi lại file phải khai báo nhiều hơn. Khi deploy, Railway CLI cũng cảnh báo `railway.toml` đã deprecated và khuyên chuyển sang Infrastructure as Code.

Hai file mẫu trong `03-cloud-deployment/` khác bản trên ở cách build: Railway dùng `NIXPACKS` với `startCommand`, Render dùng `runtime: python` với `buildCommand`, tức không dùng Dockerfile.

### Exercise 3.3: Pipeline CI/CD Cloud Run

Đọc `cloudbuild.yaml` và `service.yaml` (không deploy):

1. **Test:** cài dependencies và chạy `pytest`; các bước nối nhau bằng `waitFor`, nên test lỗi thì dừng pipeline.
2. **Build:** tạo Docker image gắn tag `$COMMIT_SHA` và `latest`, dùng `--cache-from` để tận dụng layer cũ.
3. **Push:** đẩy image lên Container Registry (`gcr.io`).
4. **Deploy:** `gcloud run deploy` bản `$COMMIT_SHA` tại `asia-southeast1`, 1–10 instance, 512Mi, secret lấy từ Secret Manager.
5. `service.yaml` mô tả service: concurrency 80, giới hạn tài nguyên, liveness probe `/health`, startup probe `/ready`.

Bước test cần `requirements.txt` và thư mục `tests/`, hiện không có trong `production-cloud-run/`.

## Part 4: API Security

### Exercise 4.1: API Key authentication

File xét: `04-api-gateway/develop/app.py`.

- **Key được kiểm tra ở đâu:** hàm `verify_api_key` (dòng 39–54) đọc header `X-API-Key`, so với biến môi trường `AGENT_API_KEY` (dòng 35). `/ask` gắn hàm này qua `Depends` (dòng 70). `/health` và `/` không cần key.
- **Sai key thì sao:** thiếu key trả 401, sai key trả 403, request không tới được agent.
- **Rotate key:** đổi giá trị `AGENT_API_KEY` rồi khởi động lại, không cần sửa code. Muốn không gián đoạn thì cho server nhận cả key cũ và key mới trong thời gian chuyển đổi, sau đó bỏ key cũ.
- **Điểm yếu:** có key mặc định trong code (dòng 35) và in key ra màn hình lúc khởi động (dòng 91).

```text
$ curl -i -X POST $U -H "Content-Type: application/json" -d "$B"; echo
HTTP/1.1 401 Unauthorized
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

$ curl -i -X POST $U -H "X-API-Key: wrong" -H "Content-Type: application/json" -d "$B"; echo
HTTP/1.1 403 Forbidden
{"detail":"Invalid API key."}

$ curl -i -X POST $U -H "X-API-Key: <key>" -H "Content-Type: application/json" -d "$B"; echo
HTTP/1.1 200 OK
{"question":"Hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

Trong đó `U=http://localhost:8000/ask`, `B='{"question":"Hello"}'`.

### Exercise 4.2: JWT authentication

Luồng trong `04-api-gateway/production/auth.py`:

1. `POST /auth/token` với username, password; `authenticate_user` (dòng 70–75) kiểm tra.
2. `create_token` (dòng 35–43) ký token HS256 chứa `sub`, `role`, `iat`, `exp` (hết hạn sau 60 phút).
3. Client gửi `Authorization: Bearer <token>`.
4. `verify_token` (dòng 46–67) kiểm tra chữ ký và hạn, lấy user và role mà không cần tra database. Theo code: thiếu token hoặc hết hạn trả 401, token sai trả 403.

```text
$ curl -i -X POST $U -H "Content-Type: application/json" -d "$B"; echo
HTTP/1.1 401 Unauthorized
date: Thu, 26 Nov 2026 09:00:31 GMT
www-authenticate: Bearer
{"detail":"Authentication required. Include: Authorization: Bearer <token>"}

$ TOKEN=$(curl -s -X POST http://localhost:8000/auth/token -H "Content-Type: application/json" \
    -d '{"username":"student","password":"demo123"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

$ curl -i -X POST $U -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$B"; echo
HTTP/1.1 200 OK
date: Thu, 26 Nov 2026 09:00:54 GMT
{"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":9,"budget_remaining_usd":1.8e-05}}
```

Điểm yếu của bản demo: `JWT_SECRET` có giá trị mặc định trong code (dòng 22), mật khẩu lưu dạng rõ (dòng 27–30), token đã cấp không thu hồi được trước khi hết hạn.

### Exercise 4.3: Rate limiting

- **Thuật toán:** sliding window lưu timestamp từng request trong `deque` (`rate_limiter.py` 29–71). Mỗi lần gọi, bỏ các mốc cũ hơn 60 giây rồi đếm. Comment gọi là "Sliding Window Counter" nhưng cách làm thực tế là sliding window log.
- **Giới hạn:** user 10 request/phút, admin 100 request/phút (dòng 86–87).
- **Admin:** không bỏ qua hoàn toàn; `app.py` 141 chọn limiter theo `role` trong token, nên tài khoản `teacher` có mức 100. Role nằm trong token đã ký nên client không tự sửa được nếu không biết secret.

```text
$ for i in {1..20}; do echo -n "request $i: "; curl -s -o /dev/null -w '%{http_code}\n' -X POST $U \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$B"; done
request 1: 200
request 2: 200
request 3: 200
request 4: 200
request 5: 200
request 6: 200
request 7: 200
request 8: 200
request 9: 200
request 10: 429
request 11: 429
request 12: 429
request 13: 429
request 14: 429
request 15: 429
request 16: 429
request 17: 429
request 18: 429
request 19: 429
request 20: 429

$ curl -i -X POST $U -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$B"; echo
HTTP/1.1 429 Too Many Requests
date: Thu, 26 Nov 2026 09:01:05 GMT
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
x-ratelimit-reset: 1795683726
retry-after: 49
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":49}}
```

- 429 bắt đầu từ request 10 của vòng lặp vì lệnh curl trước đó đã dùng 1 trong 10 lượt.
- `retry-after: 49` là thời gian còn lại đến khi request cũ nhất (lúc 09:00:54) ra khỏi cửa sổ 60 giây.
- Request bị 429 không được ghi vào cửa sổ (dòng 65 chỉ chạy khi chưa vượt).

### Exercise 4.4: Cost guard

**Cách code hiện tại làm** (`cost_guard.py`):

1. Trước khi gọi LLM, `check_budget` (dòng 60–91): chi phí cả hệ thống đạt $10 thì trả 503; chi phí của user trong ngày đạt $1 thì trả 402; từ 80% thì ghi cảnh báo.
2. Sau khi gọi LLM, `record_usage` (dòng 93–110) cộng token và chi phí: $0.00015 / 1K token input, $0.0006 / 1K token output.
3. Bản ghi theo user được tạo mới khi sang ngày khác (dòng 53–58).

```text
$ curl -s http://localhost:8000/me/usage -H "Authorization: Bearer $TOKEN"; echo
{"user_id":"student","date":"2026-11-26","requests":10,"input_tokens":20,"output_tokens":308,"cost_usd":0.000188,"budget_usd":1.0,"budget_remaining_usd":0.999812,"budget_used_pct":0.0}
```

- `requests: 10` đúng bằng số request trả 200; request bị 429 không tốn tiền.
- Kiểm tra: 20 / 1000 × 0.00015 + 308 / 1000 × 0.0006 ≈ $0.000188.

**Hạn chế quan sát và đọc được**

- Trường `budget_remaining_usd` trong response của `/ask` thực ra là số **đã dùng** (`app.py` 160): response báo `1.8e-05` trong khi `/me/usage` cho thấy còn lại gần $1.
- `_global_cost` chỉ được cộng, không có code reset theo ngày, nên ngân sách chung chỉ về 0 khi khởi động lại.
- Dữ liệu nằm trong RAM: restart là mất, chạy nhiều instance thì mỗi instance đếm riêng.
- Kiểm tra trước, ghi sau nên nhiều request đồng thời có thể cùng lọt qua và vượt ngân sách.

**Đề xuất cho production (chưa chạy thử):** lưu tổng chi phí trong Redis với key theo user và ngày, cộng bằng `INCRBYFLOAT`, đặt TTL; muốn không vượt khi có request đồng thời thì giữ trước chi phí ước tính bằng một Lua script (kiểm tra và cộng trong một bước), sau đó điều chỉnh theo chi phí thật.

**Vì sao cần cả rate limit và cost guard:** rate limit giới hạn tốc độ gọi, bảo vệ server; cost guard giới hạn tổng tiền. Gọi chậm đều vẫn có thể tiêu hết ngân sách, còn một đợt gọi dồn dập có thể làm quá tải trước khi chạm ngân sách.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

File xét: `05-scaling-reliability/develop/app.py`.

| Endpoint | Loại | Trả lời câu hỏi | Khi fail thì nền tảng làm gì |
|---|---|---|---|
| `GET /health` (104–144) | Liveness | Process còn sống không? | Restart container |
| `GET /ready` (147–168) | Readiness | Nhận traffic được chưa? | Ngừng gửi request tới instance, không restart |

```text
$ curl -i http://localhost:8000/health; echo
HTTP/1.1 200 OK
{"status":"ok","uptime_seconds":5.8,"version":"1.0.0","environment":"development","timestamp":"2026-11-26T09:03:53.104848+00:00","checks":{"memory":{"status":"ok","used_percent":12.1}}}

$ curl -i http://localhost:8000/ready; echo
HTTP/1.1 200 OK
{"ready":true,"in_flight_requests":1}
```

`in_flight_requests: 1` là chính request `/ready` đang được đếm.

### Exercise 5.2: Graceful shutdown

Gửi một request mất khoảng 3 giây, 0,5 giây sau gửi SIGTERM (chạy bằng script, server ở `PORT=8765`):

```text
request sent  09:16:12.985
SIGTERM sent  09:16:13.485
HTTP/1.1 200 OK
{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
response done 09:16:16.045
server exit code 0
```

```text
INFO:     Shutting down
INFO:     127.0.0.1:53040 - "POST /ask?question=hello HTTP/1.1" 200 OK
INFO:     Waiting for application shutdown.
2026-11-26 09:16:16,142 INFO 🔄 Graceful shutdown initiated...
2026-11-26 09:16:16,143 INFO ✅ Shutdown complete
INFO:     Application shutdown complete.
INFO:     Finished server process [4132]
2026-11-26 09:16:16,144 INFO Received signal 15 — uvicorn will handle graceful shutdown
```

- Request đang chạy **không bị cắt**: SIGTERM đến khoảng 2,5 giây trước khi có response, vẫn nhận 200 và process thoát với exit code 0.
- Việc chờ request do **uvicorn** làm (`timeout_graceful_shutdown=30`, dòng 198). Phần shutdown của `lifespan` chỉ chạy sau khi request xong, nên vòng lặp chờ (dòng 58–64) không in dòng `Waiting for ... in-flight` nào.
- Do đó `_is_ready = False` cũng chỉ được đặt sau khi request xong, không phải ngay lúc nhận SIGTERM.
- `Received signal 15` in cuối cùng: handler tự đăng ký được gọi lại sau khi uvicorn tắt xong.
- Đọc từ code: `/ask` là `async def` nhưng gọi hàm mock dùng `time.sleep`, nên trong 3 giây đó event loop bị chặn.

### Exercise 5.3: Stateless design

- **Vấn đề:** nếu history nằm trong RAM, mỗi instance chỉ thấy phần của mình; request sau rơi vào instance khác là mất ngữ cảnh, restart là mất sạch.
- **Cách làm trong `production/app.py`:** session lưu ở Redis với key `session:<id>`, TTL 1 giờ (dòng 59–90). Instance nào cũng đọc ghi được.
- **Hạn chế đọc từ code:**
  - Không kết nối được Redis lúc khởi động thì tự chuyển sang dict trong RAM (dòng 35–45), nhiều instance sẽ sai mà không báo lỗi.
  - `append_to_history` đọc rồi ghi lại cả session, hai request đồng thời cùng session có thể ghi đè nhau.
  - `/health` vẫn trả 200 khi Redis mất (`status: degraded`).

### Exercise 5.4: Load balancing

```text
$ docker compose -p k5-day14-scaling up -d --build --scale agent=3
$ docker compose -p k5-day14-scaling ps
NAME                       STATUS                    PORTS
k5-day14-scaling-agent-1   Up 36 seconds (healthy)   8000/tcp
k5-day14-scaling-agent-2   Up 36 seconds (healthy)   8000/tcp
k5-day14-scaling-agent-3   Up 36 seconds (healthy)   8000/tcp
k5-day14-scaling-nginx-1   Up 36 seconds             0.0.0.0:8080->80/tcp
k5-day14-scaling-redis-1   Up 47 seconds (healthy)   6379/tcp
```

Nginx (cổng 8080) phân request cho 3 instance; chỉ Nginx mở cổng ra ngoài.

### Exercise 5.5: Test stateless

```text
$ python3 test_stateless.py
Session ID: 4138d272-f92e-4f57-808b-1e5a5e409917
Request 1: [instance-248748]
Request 2: [instance-2bd16c]
Request 3: [instance-9b9705]
Request 4: [instance-248748]
Request 5: [instance-2bd16c]
Instances used: {'instance-2bd16c', 'instance-9b9705', 'instance-248748'}
Total messages: 10
✅ Session history preserved across all instances via Redis!
```

5 request đi qua 3 instance theo vòng, history vẫn đủ 10 message.

**Tắt một instance rồi hỏi tiếp** (`test_stateless.py` không tự làm bước này; chạy bằng script, session mới):

```text
Session ID: 37d70deb-b5f3-414a-aa38-91284557e2c9   (5 câu đầu, count = 10)
$ docker kill k5-day14-scaling-agent-1             # instance-af9111, đã xử lý request 2 và 5
k5-day14-scaling-agent-1   Exited (137)
k5-day14-scaling-agent-2   Up (healthy)
k5-day14-scaling-agent-3   Up (healthy)

$ POST /chat "Still there?" cùng session_id
{"session_id":"37d70deb-...","turn":7,"served_by":"instance-3c2480","storage":"redis", ...}
HTTP 200 time 0.151710s

$ GET /chat/37d70deb-.../history
{"session_id":"37d70deb-...","messages":[...],"count":12}
HTTP 200 time 60.191262s
```

- Instance khác phục vụ tiếp và history còn đủ 12 message: state nằm trong Redis, không phụ thuộc instance bị tắt.
- Request `GET` mất **60,2 giây**, trùng với `proxy_connect_timeout` mặc định 60 giây của Nginx. Nguyên nhân nhiều khả năng (chưa kiểm tra log Nginx): `nginx.conf` phân giải `agent` lúc khởi động và không đặt timeout kết nối, nên Nginx vẫn thử IP của container đã chết, hết thời gian chờ mới chuyển sang instance khác. Có thể giảm bằng `proxy_connect_timeout` ngắn và `server agent:8000 resolve`.
- `turn` báo 7 cho câu hỏi thứ 6: history được đọc sau khi đã thêm câu hiện tại rồi vẫn cộng 1 (`production/app.py` 154).

## Part 6: Final Project

Output của `python check_production_ready.py` (chạy đầy đủ, có Docker, trong `06-lab-complete/`):

```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 43/43 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

Chạy thử cả stack bằng `docker compose -p k5-day14-lab up -d --build`:

| Request | Mã HTTP |
|---|---|
| `GET /health` | 200 |
| `GET /ready` | 200 |
| `POST /ask` không có key | 401 |
| `POST /ask` có `X-API-Key` | 200 |

## AI log

| Hỏi gì | Nhận gì | Tôi tự sửa và kiểm tra thế nào |
|---|---|---|
| Hỏi Claude kiểm tra lệnh khớp bài chưa | Đã khớp; gán giúp lệnh chạy | Tự chạy các lệnh trong WSL.  |
| Nhờ Claude kiểm tra và hoàn thiện Part 1 | Claude đề xuất thí nghiệm SIGTERM; soạn Exercise 1.1, 1.2, 1.3 (bảng, nhận xét, phân tích lỗi) từ code trong repo và output tôi chạy | Tự chạy các lệnh và thí nghiệm trong WSL. |
| Nhờ Claude hoàn thiện Part 2 | Claude soạn Exercise 2.1–2.4 (câu trả lời, bảng kích thước, sơ đồ, nhận xét) từ code trong repo và output tôi chạy; Claude chạy `docker history` trên máy này để phân tích layer | Tự chạy build, container và Docker Compose trong WSL. |
| Hỏi Claude cách chạy Part 4, sửa lỗi chạy nhầm server, và soạn bài | Claude chỉ ra server đang chạy sai thư mục; soạn Exercise 4.1–4.4 từ code trong repo và output tôi chạy | Tự chạy các lệnh curl cho bản develop và production trong WSL. |
| Nhờ Claude tự thực hiện phần còn lại của Part 5 và soạn bài | Claude viết script cho thí nghiệm SIGTERM (5.2) và kill instance (5.5), chạy thử trên máy này; soạn Exercise 5.1–5.5 | Tự chạy health/ready, Docker Compose 3 instance, `test_stateless.py` và tự chạy lại script; số liệu 5.2 và phần kill instance lấy từ lần tôi chạy. |
| Nhờ Claude làm Part 6 từng bước | Claude viết code trong `06-lab-complete/app/`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `railway.toml`, `render.yaml`, `.env.example` theo 9 bước kèm giải thích; chạy `check_production_ready.py` để kiểm tra | Tự kiểm tra trong WSL: đọc config từ env, API key (401/200), tắt Redis (`/ready` 503), rate limit (429), cost guard (402), SIGTERM, `docker build`/`run`/`stop`, Docker Compose và `check_production_ready.py` PASS 12/12. |
| Nhờ Claude hướng dẫn deploy Railway, xử lý lỗi 401 và soạn Part 3 | Claude đưa lệnh Railway; kiểm tra độ dài biến trên Railway và gọi thử `/ask` để tìm lỗi; kiểm tra ảnh; soạn `DEPLOYMENT.md` và mục Part 3 | Tự deploy, tự chạy 4 lệnh kiểm tra trên URL public và tự chụp 3 ảnh. |
