# Session 05 — HTTP 503 và phục hồi HTTP 200 trên AWS

- Ngày: 2026-10-30, giờ Asia/Saigon.
- Mục tiêu: kiểm thử thật trên AWS, đối chiếu response với CloudWatch Logs;
  không triển khai Scheduler, dashboard hoặc alarm.
- STS xác nhận Account `244477277232`; provider và lệnh AWS dùng Region
  `ap-southeast-1`, profile `fcaj-terraform`.
- Không tìm thấy AGENTS.md trên các đường dẫn áp dụng. Git ban đầu có
  `.gitignore` và workshop untracked; git diff không thể hiện các file này.

## Đối chiếu trước khi thay đổi

- AWS chỉ liệt kê một Lambda có tiền tố `fcaj-ws04`:
  `fcaj-ws04-Web_monitoring`, khớp Terraform và state.
  Tên `fcaj-ws04-monitoring` được nêu trong yêu cầu không có trong danh sách.
- Đã tải deployment package vào thư mục tạm; không in/lưu URL tải có chữ ký.
  `app.py` triển khai trùng từng byte với `src/app.py`; không triển khai lại mã.
- SHA-256 của hai file app.py:
  `766f9be24bca81191ae7bdebaa13eff6800a387b0bb6fb6dcfcbdd284d6c5bac`.
- TARGET_URL ban đầu: `https://example.com`; biến còn lại:
  `HTTP_TIMEOUT_SECONDS=5`. Terraform quản lý URL qua biến `target_url`
  trong `infra/lambda.tf`; dùng `-var` tạm thời, không sửa giá trị mặc định.
- Endpoint lỗi: `https://httpbin.org/status/503`, phụ thuộc dịch vụ kiểm thử
  công khai bên ngoài. Kết luận dưới đây dựa trên HTTP 503 do Lambda thực nhận.

## Kết quả thực tế

| Pha | Giờ Việt Nam | HTTP | is_healthy | error | Log JSON khớp response |
|---|---|---|---|---|---|
| Lỗi | 11:29:02 | 503 | false | HTTP 503 | Có |
| Phục hồi | 11:30:03 | 200 | true | null | Có |

- Request lỗi: `b8b68603-011e-4a0a-95fd-31b777c5507d`.
- Request phục hồi: `b05255ba-54b9-406d-9aec-70980657c9ef`.
- Thực hiện một lệnh invoke đồng bộ mỗi pha, không chạy vòng lặp tải.
  Invoke metadata đều StatusCode=200, không có FunctionError; đây là trạng thái
  invoke Lambda, tách biệt với HTTP của website trong payload.
- Mỗi pha có một log JSON ứng dụng được đối chiếu toàn bộ nội dung với response.
  Log group: `/aws/lambda/fcaj-ws04-Web_monitoring`.

## Minh chứng mới

Thư mục riêng: [session05-2026-10-30-mvugznnk](../evidence/session05-2026-10-30-mvugznnk/).

- [Response HTTP 503](../evidence/session05-2026-10-30-mvugznnk/failure-response.json)
  và [log xác nhận](../evidence/session05-2026-10-30-mvugznnk/failure-cloudwatch-confirmed.json).
- [Response phục hồi 200](../evidence/session05-2026-10-30-mvugznnk/recovery-response.json)
  và [log xác nhận](../evidence/session05-2026-10-30-mvugznnk/recovery-cloudwatch-confirmed.json).
- [Tổng hợp đã xác minh](../evidence/session05-2026-10-30-mvugznnk/verified-summary.json).
- Invoke metadata: `failure-invoke.json`, `recovery-invoke.json`.
- Plan đã kiểm tra: `failure-plan-summary.json`,
  `restore-plan-summary.json`, `final-plan-summary.json`.

## Khôi phục và Terraform

- Cả plan gây lỗi và plan khôi phục đều được kiểm tra trước apply:
  **0 thêm, 1 cập nhật tại chỗ, 0 xóa**, chỉ thay đổi TARGET_URL.
- Script kiểm tra JSON plan trong bộ nhớ, từ chối thay đổi thuộc tính khác,
  giữ nguyên biến môi trường còn lại; dùng khối finally để ưu tiên khôi phục.
- Đã khôi phục chính xác `TARGET_URL=https://example.com`; toàn bộ biến môi trường
  và code hash khớp ban đầu, LastUpdateStatus=Successful, State=Active.
- Plan cuối với URL ban đầu: **không có thay đổi resource hoặc output**.
- Saved plans và state/backup do Terraform quản lý nằm trong infra, được Git
  ignore; không xuất toàn bộ state vào báo cáo.
- Không sửa `src/app.py` hoặc các file `.tf`; không commit/push hoặc destroy.

## Lỗi và cách xử lý

- STS trong sandbox gặp proxy `http://127.0.0.1:9`; chạy lại ngoài sandbox
  theo cơ chế cấp quyền thành công. Đây là lỗi môi trường, không phải lỗi app.
- Truy vấn log đầu tiên dùng UUID chưa đặt trong ngoặc kép nên không khớp.
  Sửa thành chuỗi được bao bởi dấu ngoặc kép theo cú pháp CloudWatch; đọc lại
  đúng hai request_id và xác nhận thành công, không gọi thêm Lambda.
- Giữ nguyên kết quả truy vấn ban đầu tại `*-cloudwatch.json` và
  `summary.json` (passed=false do chưa tìm được log). Kết quả cuối đã đối chiếu
  nằm trong `*-cloudwatch-confirmed.json` và `verified-summary.json`.
- Không có dữ liệu mock trong minh chứng AWS; không ghi đè minh chứng buổi trước.

## File mới và giới hạn

- [Script thực nghiệm](../scripts/session05_failure_recovery.py): kiểm tra plan,
  invoke, lấy log, khôi phục và kiểm tra drift. Đây là script có thể thay đổi AWS
  khi chạy chế độ chính; không thuộc bộ test mock local. Chế độ
  `--verify-existing-logs` chỉ đọc log và evidence có sẵn.
- Nhật ký này và thư mục evidence nêu trên được thêm mới.
- Đã kiểm tra fmt/validate trước thực nghiệm: đều đạt.
- Chưa kiểm chứng lỗi DNS/timeout thực tế, độ ổn định dài hạn, Scheduler,
  dashboard hoặc alarm. Kết quả chỉ mô tả hai lần gọi trong buổi này.
- Bước tiếp theo đề xuất: thiết kế EventBridge Scheduler trong chặng riêng,
  xem plan và quyền invoke trước khi triển khai.

## Tham khảo

- [httpbin — HTTP Request & Response Service](https://httpbin.org/)
- [AWS — synchronous invocation](https://docs.aws.amazon.com/lambda/latest/dg/invocation-sync.html)
- [AWS — filter pattern, quy tắc ngoặc kép cho ký tự đặc biệt](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html)
- [HashiCorp — apply saved plan](https://developer.hashicorp.com/terraform/cli/commands/apply)
