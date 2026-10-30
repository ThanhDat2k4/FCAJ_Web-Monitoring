# Session 04 — Kiểm thử mock local và đọc trạng thái AWS

- Ngày: 2026-10-30 (Asia/Saigon).
- Phạm vi: bổ sung test local, kiểm tra cấu hình, đọc AWS; không gọi Lambda,
  không plan/apply/destroy, không commit/push.
- Không tìm thấy AGENTS.md tại `D:\`, workspace hoặc trong workshop;
  áp dụng hướng dẫn người dùng đã cung cấp trong hội thoại.
- Git ban đầu: `.gitignore` và toàn bộ workshop đang untracked.
  Không stage, sửa hoặc xóa các file có sẵn.

## Trạng thái đã xác minh

### Code local

- Đã đọc `src/app.py`, bốn file `.tf`, tài liệu các buổi trước và response JSON cũ.
- AWS provider: profile `fcaj-terraform`, Region `ap-southeast-1`,
  `allowed_account_ids = ["244477277232"]`.
- Terraform khai báo IAM role, inline logging policy, log group và Lambda.
- Lambda: `app.lambda_handler`, Python 3.13, timeout 15 giây, RAM 128 MB;
  URL mặc định `https://example.com`, HTTP timeout 5 giây.
- Code lấy URL từ môi trường; HTTP 2xx là healthy; HTTPError giữ mã HTTP;
  lỗi kết nối/timeout trả `http_status=null`, `is_healthy=false` và chuỗi lỗi.
- Chưa có khai báo Scheduler, custom metrics, dashboard, alarm trong code đã đọc.
- Tài liệu buổi 02 dùng tên tài nguyên cũ khác code hiện tại. Giữ nguyên lịch sử;
  tên tài nguyên xác minh lần này nằm ở phần AWS bên dưới.

### AWS chỉ đọc

Mọi lệnh tài nguyên đều dùng `--profile fcaj-terraform --region ap-southeast-1`.
Chỉ truy vấn tài nguyên sau khi STS xác nhận đúng Account ID.

| Kiểm tra | Kết quả quan sát |
|---|---|
| `aws sts get-caller-identity --profile fcaj-terraform` | Account `244477277232`; ARN `arn:aws:iam::244477277232:root` |
| Lambda `get-function-configuration` | `fcaj-ws04-Web_monitoring`: Active, LastUpdateStatus Successful; runtime, handler, timeout, RAM và hai biến cấu hình nêu trên khớp code |
| Execution role | `fcaj-ws04-Web_monitoring-lambda-role`; role Lambda đang dùng khớp role đã đọc |
| IAM `get-role` | Trust cho `lambda.amazonaws.com` thực hiện `sts:AssumeRole` |
| IAM `get-role-policy` | `fcaj-ws04-Web_monitoring-write-logs`: cho phép CreateLogStream, PutLogEvents trong `/aws/lambda/fcaj-ws04-Web_monitoring:*` |
| IAM list policies | Một inline policy nêu trên; không có managed policy gắn trực tiếp |
| Logs `describe-log-groups` | `/aws/lambda/fcaj-ws04-Web_monitoring`, retention 1 ngày |
| Scheduler `list-schedules --name-prefix fcaj` | Danh sách rỗng |
| CloudWatch `list-dashboards --dashboard-name-prefix fcaj` | Danh sách rỗng |
| CloudWatch `describe-alarms --alarm-name-prefix fcaj` | Metric alarms và composite alarms đều rỗng |
| CloudWatch `list-metrics --dimensions Name=FunctionName,Value=fcaj-ws04-Web_monitoring` | Chỉ thấy namespace AWS/Lambda: Errors, ConcurrentExecutions, Invocations, Duration, Throttles |
| Logs `describe-metric-filters` trên log group WS04 | Danh sách rỗng |
| Logs `filter-log-events` theo request_id cũ `700f131e-7f10-4ce3-8fb5-90063b08cf9a` | Không trả event; chưa đối chiếu lại được log thực tế |

Giới hạn: các truy vấn theo tiền tố tên hoặc dimension không chứng minh toàn bộ
tài khoản không có Scheduler/dashboard/alarm/custom metrics dùng tên hoặc dimension
khác. Không kết luận nguyên nhân log cũ không xuất hiện. Chưa tải mã triển khai
để đối chiếu nội dung với `app.py`, chưa đánh giá đầy đủ quyền hiệu lực IAM.

## Kiểm thử local

Chạy từ `D:\FCAJ-Workshops-2026\ws04-Web_monitoring`:

```powershell
python -B -m unittest discover -s tests -v
```

Kết quả: **5 tests, OK** trên Python 3.14.7 local (khác runtime AWS Python 3.13).

| Test | is_healthy | http_status | error |
|---|---|---|---|
| HTTP 200 | true | 200 | null |
| HTTP 503 qua HTTPError | false | 503 | HTTP 503 |
| URLError kết nối | false | null | <urlopen error connection refused> |
| TimeoutError trực tiếp | false | null | timed out |
| TimeoutError bọc trong URLError | false | null | <urlopen error timed out> |

Mọi test kiểm tra request_id giả `local-mock-request-id`, log JSON bằng kết quả
trả về, URL và HTTP timeout truyền vào request. Test HTTP 200 còn kiểm tra URL
trong event không ghi đè cấu hình. Test 503 kiểm tra đóng response lỗi.
Mock `src.app.urlopen` tại nơi handler sử dụng; không gửi HTTP hoặc gọi AWS.
Log mock được giữ trong bộ nhớ, không ghi vào thư mục evidence.

Chạy từ `infra`:

```powershell
terraform fmt -check -diff
terraform validate -no-color
```

- Cả hai đạt; validate: `Success! The configuration is valid.`
- Đây là kiểm tra cấu hình local, không chứng minh AWS không có drift.
- Không phát hiện lỗi ứng dụng trong các trường hợp đã kiểm thử; không sửa
  `src/app.py` hoặc Terraform.

## Lỗi môi trường và cách xử lý

- STS trong sandbox thất bại với:
  `Error when retrieving credentials from custom-process` và
  `Failed to connect to proxy URL: "http://127.0.0.1:9"`.
- Chạy lại STS ngoài sandbox theo cơ chế cấp quyền: thành công. Các truy vấn AWS
  sau đó cũng chạy ngoài sandbox. Không quy lỗi proxy thành lỗi ứng dụng hoặc
  kết luận credentials hết hạn; không đọc nội dung credentials.
- Buổi 03 nhắc ảnh `03_lambda-cloudwatch-log.png`, nhưng không tìm thấy file đó
  trong danh sách evidence hiện tại. Không tự tạo minh chứng thay thế.
- Response JSON cũ vẫn ghi HTTP 200, healthy=true và latency 452.76 ms;
  đây là dữ liệu thực nghiệm cũ, không phải lần gọi Lambda mới.

## Thay đổi và bước tiếp theo

- Thêm `tests/test_app.py` và nhật ký này. Giữ nguyên tài liệu và evidence cũ.
- Chưa kiểm thử lỗi/phục hồi trên AWS và chưa chạy test bằng Python 3.13.
- Chặng tiếp: chuẩn bị một endpoint kiểm thử có thể chủ động trả 503 rồi 200;
  khi được phép thay đổi AWS, kiểm tra lỗi/phục hồi, đối chiếu request_id và
  CloudWatch Logs, lưu minh chứng mới riêng biệt.
- Sau đó triển khai EventBridge Scheduler theo một chặng riêng: xác định chu kỳ,
  role/quyền invoke, kiểm tra plan trước khi triển khai và xác minh các lần chạy.

## Tài liệu đã tham khảo

- [Python unittest.mock — patch tại nơi đối tượng được tra cứu](https://docs.python.org/3/library/unittest.mock.html#where-to-patch)
- [Python urllib.error — HTTPError và URLError](https://docs.python.org/3/library/urllib.error.html)
- [HashiCorp — giới hạn của terraform validate](https://developer.hashicorp.com/terraform/cli/commands/validate)
