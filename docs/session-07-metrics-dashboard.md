# Session 07 — Custom metrics và CloudWatch dashboard

- Ngày: 2026-10-30 (Asia/Saigon); Account `244477277232`, Region
  `ap-southeast-1`, profile `fcaj-terraform`.
- Đã đọc code/Terraform/test, kiểm tra Git và các đường dẫn AGENTS.md áp dụng
  (không tìm thấy file). Workshop vẫn untracked; không ghi đè thay đổi có sẵn.
- Trước sửa: Scheduler DISABLED, TARGET_URL `https://example.com`, plan không
  có drift. Không bật Scheduler trong chặng này.

## Kết quả AWS và minh chứng

- Invoke đồng bộ **đúng một lần**, lúc **14:00:16 ngày 30/10/2026** (giờ Việt Nam):
  HTTP **200**, healthy=true, error=null, latency **455,59 ms**.
- Request_id: `3156cdd1-0687-4d98-98fe-549e3bfb35f5`; log JSON khớp toàn bộ
  nội dung response, không chỉ request_id.
- Sau **2 đợt polling chỉ đọc**, truy vấn đúng namespace/dimension ở period 60:

| Datapoint (giờ Việt Nam) | Metric | Minimum / Average / Maximum | SampleCount | Unit |
|---|---|---|---|---|
| 14:00:00 | Availability | 1 / 1 / 1 | 1 | None |
| 14:00:00 | Latency | 455,59 / 455,59 / 455,59 | 1 | Milliseconds |

Các giá trị khớp kết quả kiểm tra trong cùng phút. Metric không chứa request_id;
việc đối chiếu dựa trên thời gian, giá trị và SampleCount=1, không phải liên kết
request_id trực tiếp trong CloudWatch metric.

- Dashboard đã kiểm tra bằng API, JSON khớp plan; **chưa kiểm chứng Console UI**.
- Kết thúc: Scheduler **DISABLED, cấu hình không đổi**, Lambda giữ nguyên
  cấu hình ngoài code; Terraform **không còn thay đổi resource/output**.
- Minh chứng mới: [session07-2026-10-30-mvultcfx](../evidence/session07-2026-10-30-mvultcfx/), gồm
  [response](../evidence/session07-2026-10-30-mvultcfx/response.json),
  [log](../evidence/session07-2026-10-30-mvultcfx/cloudwatch-log.json),
  [datapoints và tham số truy vấn](../evidence/session07-2026-10-30-mvultcfx/metrics.json),
  [dashboard API](../evidence/session07-2026-10-30-mvultcfx/dashboard-api.json),
  [test exit_code=0](../evidence/session07-2026-10-30-mvultcfx/local-tests-verified.json),
  [plan cuối](../evidence/session07-2026-10-30-mvultcfx/verified-final-plan-summary.json),
  [tổng hợp cuối](../evidence/session07-2026-10-30-mvultcfx/verified-summary.json).
  `summary.json` giữ kết quả lần kiểm tra đầu bị lỗi encoding, chưa invoke;
  `verified-summary.json` là kết quả cuối sau khắc phục.

## Ý nghĩa và cách phát metrics

Namespace `FCAJ/WebsiteMonitoring`, dimension duy nhất `MonitorId=ws04-main`.

| Metric | Giá trị và unit | Dashboard |
|---|---|---|
| Availability | Healthy: 1; unhealthy: 0; Unit=None | Minimum, period 300, Y từ 0 đến 1 |
| Latency | `latency_ms`; Milliseconds | Average và Maximum, period 300, trục ms |

- Hai metrics được gửi trong một PutMetricData, standard resolution 60 giây;
  timestamp trùng kết quả kiểm tra. Resolution khác period hiển thị 300 giây.
- Latency giữ nguyên phép đo HTTP hiện có, có thể bao gồm thời gian trước khi
  lỗi xảy ra; không phải tải toàn trang và không gồm thời gian phát metric.
- Không dùng URL, request_id hoặc timestamp làm dimension. Log và response
  website_check giữ nguyên các trường cũ.
- Nếu phát metric lỗi: ghi event riêng `metrics_publish_error`, request_id,
  loại/thông báo lỗi rồi raise. Không thay lỗi HTTP của website bằng lỗi SDK,
  không trả thành công khi metric chưa phát được.
- SDK boto3/botocore dùng bản có sẵn trong Lambda, chỉ tạo client khi cần;
  timeout SDK giới hạn và không retry. Test mock helper client nên không cần
  credentials, AWS thật hoặc cài dependency test mới (chỉ unittest chuẩn).

## IAM, dashboard và phạm vi triển khai

- Thêm inline policy `fcaj-ws04-Web_monitoring-publish-metrics` cho Lambda role:
  chỉ `cloudwatch:PutMetricData`, Resource=`*`, StringEquals giới hạn
  `cloudwatch:namespace=FCAJ/WebsiteMonitoring`. Không mở rộng logging policy
  hoặc Scheduler role. Resource `*` là cách cấp quyền action này theo tài liệu
  AWS, được giới hạn thêm bởi namespace condition.
- Dashboard `fcaj-ws04-Web_monitoring`: 3 metric widgets và 1 text widget.
  Widget native dùng AWS/Lambda Invocations và Errors, FunctionName đúng hàm,
  Sum/300 giây. Mọi metric widget ở ap-southeast-1.
- Không FILL hoặc mặc định missing=healthy. Khoảng thiếu dữ liệu không chứng
  minh website khỏe, một sample 1 không chứng minh khỏe liên tục cả 5 phút.
- Saved plan: **2 create, 1 update code Lambda, 0 destroy**; đã kiểm tra trước
  apply. Không đổi TARGET_URL, runtime, retention, Scheduler hoặc quyền cũ.
- Thêm dependency để policy metrics sẵn sàng trước khi cập nhật code Lambda.

## Kiểm thử và lỗi môi trường

- **7/7 test local đạt**: giữ HTTP 200/503/kết nối/hai dạng timeout; kiểm tra
  payload hai metrics trong mọi trường hợp; lỗi publish sau HTTP 200 hoặc 503
  được ghi log riêng và exception không bị nuốt. Chạy offline bằng:
  `python -B -m unittest discover -s tests -v`.
- Terraform fmt/validate đạt. Không trộn dữ liệu mock vào minh chứng AWS.
- STS sandbox bị lỗi proxy `http://127.0.0.1:9`; chạy lại ngoài sandbox theo
  cơ chế cấp quyền thành công, không coi đây là lỗi app.
- Lần ghi test đầu qua PowerShell biến stderr unittest thành cảnh báo;
  kết quả chuẩn có exit_code=0 được lưu riêng, không ghi đè file đầu.
- Sau apply, so sánh dashboard ban đầu bị lỗi giải mã output AWS CLI trên
  Windows, chưa invoke lúc đó. Đặt AWS_CLI_OUTPUT_ENCODING và
  AWS_CLI_FILE_ENCODING=UTF-8 cho helper subprocess; JSON API khớp đúng plan.
  Không apply lại. Giữ nguyên báo cáo lần kiểm tra đầu và lưu kết quả xác minh
  tiếp theo riêng biệt.

## Mở Console, chi phí và cleanup

Hướng dẫn cleanup tập trung sau tổng kết: [docs/cleanup.md](cleanup.md).
Các ghi chú bên dưới giữ theo ngữ cảnh session 07.

[Mở dashboard](https://ap-southeast-1.console.aws.amazon.com/cloudwatch/home?region=ap-southeast-1#dashboards:name=fcaj-ws04-Web_monitoring)

Đăng nhập đúng account, chọn Singapore và khoảng thời gian bao quanh invocation
được ghi ở trên (ví dụ 13:55–14:10 giờ Việt Nam ngày 30/10/2026). Chụp **một ảnh** thấy Availability, Latency và
Lambda widgets. Chỉ kiểm chứng cấu hình/API ở chặng này, chưa xác minh giao diện
Console hoặc cách Console vẽ các khoảng thiếu dữ liệu.

Custom metrics và dashboard **có thể phát sinh chi phí**; không khẳng định miễn
phí hoặc credit chi trả. Không có tài liệu cleanup riêng trong dự án lúc đọc.
Khi được phép cleanup: trước tiên triển khai code ngừng gọi publish metrics;
sau đó gỡ policy metrics và dependency tương ứng, resource dashboard và output
URL qua Terraform, xem plan trước mỗi apply. Ngừng phát không xóa dữ liệu cũ;
không đưa lệnh xóa trực tiếp custom metric. Chưa thực hiện cleanup lần này.

### Bổ sung cleanup chặng 8 (2026-10-30)

- Khi được phép dọn chặng 8: giữ URL ban đầu/Scheduler tắt, gỡ khai báo alarm
  trước hoặc trong plan cleanup được kiểm tra để ngừng action gửi cảnh báo.
- Gỡ email subscription, topic policy và SNS topic khỏi Terraform, xem plan
  chỉ xóa đúng tài nguyên dự định trước apply; không xóa Lambda/tài nguyên cũ
  nếu chỉ muốn dọn phần cảnh báo.
- Subscription confirmed có thể unsubscribe qua Terraform. Subscription chưa
  confirmed không thể unsubscribe độc lập; đừng coi việc xóa nó khỏi state là
  đã xóa ở AWS. Việc xóa topic sẽ xóa các subscription thuộc topic đó.
- Chỉ sau khi cấu hình không còn dùng email, mới dọn file local ignored.
  State/backup/saved plan vẫn có thể chứa địa chỉ: giữ riêng tư, không commit
  hoặc đưa vào evidence chia sẻ. Không cần lưu link xác nhận/unsubscribe.
- Chi tiết trạng thái thực nghiệm ở [session 08](session-08-alarms-sns.md);
  phần này chỉ là hướng dẫn, chưa chạy cleanup.

Chưa kiểm chứng Availability=0 hoặc lỗi PutMetricData trên AWS sau thay đổi;
hai nhánh đã được kiểm tra bằng mock. Chưa tạo alarm, SNS hoặc subscription;
không commit/push.

## File thay đổi

- Sửa `src/app.py`, `tests/test_app.py`, `infra/lambda.tf` (dependency policy).
- Thêm `infra/metrics-dashboard.tf`, `scripts/session07_metrics_dashboard.py`,
  nhật ký này và thư mục evidence riêng.
- Sửa helper `scripts/session05_failure_recovery.py` chỉ để đặt UTF-8 cho AWS
  CLI subprocess; không thay đổi lệnh hoặc minh chứng lịch sử.
- Terraform cập nhật package/state/backup và sinh saved plans được Git ignore;
  không xuất toàn bộ state hoặc ghi đè evidence cũ.

## Tham khảo

- [AWS — PutMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html)
- [AWS — namespace IAM condition](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/iam-cw-condition-keys-namespace.html)
- [AWS — dashboard JSON](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Dashboard-Body-Structure.html)
- [AWS — Lambda Python và SDK có sẵn](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [AWS CLI — output encoding](https://docs.aws.amazon.com/cli/latest/topic/config-vars.html)
- [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
