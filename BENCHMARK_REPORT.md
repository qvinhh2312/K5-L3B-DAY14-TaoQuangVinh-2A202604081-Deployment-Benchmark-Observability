# Benchmark & Observability Report — Day 14

> Mọi con số lấy từ report JSON trong `reports/`, CSV trong `benchmark-results/` và screenshot trong `screenshots/`.

**Họ tên:** 
Tào Quang Vinh

**Ngày chạy:** 26/11/2026

**Môi trường:** Windows 11, WSL2 Ubuntu 24.04 (12 CPU, 7.6 GiB RAM), Intel Core i5-11400H, Python 3.12.3, Docker 29.8.2

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | < 500 ms | p95 đo được 218–277 ms ở concurrency 1–50, ngưỡng chừa khoảng gấp đôi; ở concurrency 100 (637 ms) thì vi phạm, đúng lúc request bắt đầu phải xếp hàng |
| Error rate `/ask` | < 2 % | Mock LLM mặc định lỗi khoảng 1 %, vượt gấp đôi mức nền mới coi là bất thường |
| Accuracy trên golden dataset | ≥ 85 % | Cho phép tối đa 3/23 câu sai (v2 ban đầu đạt 91,3 %), kèm điều kiện không có regression |

### Ghi chú Exercise 7.1: metrics

- Counter: `http_requests_total` (chỉ tăng). Gauge: `agent_in_flight_requests` (lên xuống). Histogram: `http_request_duration_seconds` (đếm theo bucket `le`, dùng để tính percentile).
- Label `route` dùng mẫu route (URL lạ gộp vào `unmatched`). Nếu dùng `request.url.path`, bot quét hàng nghìn URL sẽ tạo hàng nghìn time series và làm Prometheus tốn RAM.
- Đã thêm histogram `agent_question_length_chars`. Dùng histogram thay vì label độ dài để tránh cardinality cao.

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.11 | 189.2 | 218.2 | 1695.3 | 1.67 % | PASS |
| 10 | 38.26 | 190.3 | 220.0 | 1703.9 | 0.00 % | PASS |
| 50 | 108.18 | 201.1 | 277.3 | 1706.4 | 1.33 % | PASS |
| 100 | 109.16 | 250.1 | 637.3 | 1728.8 | 3.00 % | FAIL (p95, error rate) |

Mỗi mức 300 request, `MOCK_SLOW_RATE` và `MOCK_ERROR_RATE` mặc định.

**Nhận xét:** RPS **không** tăng tuyến tính theo concurrency.

- Concurrency 1 → 10: RPS tăng 9,3 lần, gần tuyến tính, latency hầu như không đổi. Ở mức 1, RPS xấp xỉ 1 / latency trung bình (1 / 0,243 s ≈ 4,1).
- 10 → 50: concurrency tăng 5 lần, RPS chỉ tăng 2,8 lần.
- 50 → 100: RPS đứng ở khoảng 108–109, trong khi p50 tăng từ 201 lên 250 ms và p95 từ 277 lên 637 ms. Thêm request đồng thời chỉ làm chúng chờ lâu hơn, tức đã bão hoà.
- Nguyên nhân có thể: agent chạy một process (một event loop) và load generator chạy chung máy. Ở mức 50 và 100, mỗi lần đo chỉ kéo dài khoảng 2,8 s nên vài request chậm 1,7 s cũng kéo RPS xuống; muốn kết luận chắc hơn cần đo lâu hơn.
- Lỗi đều là 503 do mock LLM sinh ngẫu nhiên, không phụ thuộc tải theo code. Với 300 mẫu, tỉ lệ dao động mạnh (0 % đến 3 %), nên việc FAIL error rate ở mức 100 chưa đủ để nói do tải.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 189.3 | 218.4 | 226.2 |
| 0.03 (mặc định) | 254.0 | 224.1 | 1708.4 |
| 0.1 | 374.2 | 1690.0 | 1711.9 |

Mỗi lần 300 request, concurrency 20.

**Nhận xét:**

- **p99** nhạy nhất: chỉ 3 % request chậm đã đẩy p99 từ 226 lên 1708 ms (gấp 7,6 lần), trong khi avg chỉ tăng 65 ms và p95 gần như không đổi (vì tỉ lệ chậm nhỏ hơn 5 %).
- Ở 10 % (lớn hơn 5 %), p95 cũng nhảy lên 1690 ms (gấp 7,7 lần), avg mới tăng khoảng 2 lần. p50 vẫn quanh 189–194 ms ở cả ba mức.
- Không nên đặt SLO theo average: average trộn số ít request rất chậm vào số đông request nhanh. Ở mức 3 %, avg 254 ms trông ổn trong khi cứ khoảng 33 người có 1 người chờ hơn 1,5 s. SLO theo p95 / p99 phản ánh đúng nhóm người dùng bị chậm.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3 % (1/23) | 91.3 % (21/23) | 100 % (23/23) |
| Avg tokens / câu | 57.1 | 109.0 | 113.7 |
| Tổng cost (USD) | 0.000404 | 0.00076 | 0.00079 |
| Cost / câu đúng (USD) | 0.00040395 | 0.00003619 | 0.00003436 |
| Quality gate | FAIL (ngưỡng 80 %) | PASS (ngưỡng 80 %, không regression) | PASS (ngưỡng 100 %, không regression so với v2) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm tài liệu so sánh API key và JWT vào `KNOWLEDGE_BASE`, từ khoá kích hoạt `jwt` |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm tài liệu về Kubernetes HPA, từ khoá kích hoạt `hpa`, `kubernetes`, `autoscal` |

Chỉ sửa `develop/utils/mock_llm.py`, không sửa `golden_dataset.jsonl`.

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

- **Chất lượng:** retrieval đưa accuracy từ 4,3 % lên 91,3 %, cải thiện 20 câu, không regression.
- **Chi phí:** v2 dùng khoảng 1,9 lần token mỗi câu và tổng cost cao hơn 1,9 lần, nhưng **cost mỗi câu đúng rẻ hơn khoảng 11 lần**. So theo cost mỗi câu thì v1 có vẻ rẻ, dù phần lớn tiền trả cho câu trả lời sai.
- **Latency:** p50 trong eval tăng từ 157 lên 195 ms (thêm bước retrieval và prompt dài hơn). p95 của eval (185 so với 1537 ms) không dùng để kết luận: mẫu chỉ 23 câu, vài request chậm ngẫu nhiên đã đổi p95 (lần chạy v2 sau khi sửa KB cho p95 215,8 ms với cùng pipeline). Latency phải đọc từ load test.
- **Sau khi sửa KB:** thêm 2 câu đúng, token mỗi câu tăng từ 109,0 lên 113,7, cost mỗi câu đúng giảm nhẹ.

**Quality gate trong CI** (`.github/workflows/eval.yml`):

- Mỗi pull request: chạy agent v2, rồi `run_eval.py --min-accuracy 0.85 --baseline reports/eval_v2_fixed.json`.
- `run_eval.py` trả **exit code 1** khi accuracy dưới ngưỡng hoặc có câu trước đúng nay sai. Bước CI fail nên job đỏ.
- Để chặn merge thật sự, bật branch protection cho `main` và yêu cầu job `eval` phải pass.

Kiểm chứng exit code ở máy local (cho agent v1 chạy với baseline là v2 đã sửa):

```text
$ python eval/run_eval.py --url http://localhost:8001 --baseline reports/eval_v2_fixed.json
  ✨ Câu được cải thiện : 0
  ⚠️  Câu bị regression : 22
  Quality gate (accuracy ≥ 80%, không regression): ❌ FAIL
exit code: 1
```

Lệnh tương tự cho v2 đã sửa (baseline `eval_v2.json`, `--min-accuracy 1.0`) trả exit code 0.

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [ ] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)
- [ ] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian)
- [ ] Một trace lỗi trong Jaeger (có event `exception`)
- [ ] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | | | |
| B | `MOCK_SLOW_RATE=0.3` | | | |
| C | `LLM_MODEL=mock-llm-large` | | | |
| D | `docker pause` 1 instance | | | |
| E | `AGENT_VERSION=v1` | | | |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

...

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: ...
- Tổng thời gian: ... ms
- Span chiếm nhiều thời gian nhất: ... (... ms, ...%)
- Dòng log tương ứng (grep theo `trace_id`):

```json

```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | | | | | |
| 3 | | | | | |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

...

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. ...
  2. ...
  3. ...
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

...
