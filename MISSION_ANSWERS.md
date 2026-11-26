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

## AI log

| Hỏi gì | Nhận gì | Tôi tự sửa và kiểm tra thế nào |
|---|---|---|
| Hỏi Claude kiểm tra lệnh khớp bài chưa | Đã khớp; gán giúp lệnh chạy | Tự chạy các lệnh trong WSL.  |
| Nhờ Claude kiểm tra và hoàn thiện Part 1 | Claude đề xuất thí nghiệm SIGTERM; soạn Exercise 1.1, 1.2, 1.3 (bảng, nhận xét, phân tích lỗi) từ code trong repo và output tôi chạy | Tự chạy các lệnh và thí nghiệm trong WSL. |
