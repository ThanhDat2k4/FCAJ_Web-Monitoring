### 2026-10-30 — Lambda website check

- Công việc: Triển khai và gọi Lambda kiểm tra website; đối chiếu `request_id` giữa response và CloudWatch Logs.
- Kết quả: `https://example.com` trả HTTP 200; `is_healthy=true`; latency 452,76 ms; không ghi nhận lỗi trong lần kiểm tra này.
- Lỗi đã gặp: `ResourceNotFoundException` khi gọi Lambda lần đầu. Bổ sung nguyên nhân và cách khắc phục thực tế.
- Minh chứng: `03_lambda-response.json`, `03_lambda-cloudwatch-log.png`.
- Tiếp theo: Kiểm thử website lỗi và phục hồi.
- Tham khảo: https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs.html