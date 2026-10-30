# Session 08 — CloudWatch Alarm → SNS → email

- Ngày: 2026-10-30, Asia/Saigon.
- Account `244477277232`; Region `ap-southeast-1`; profile `fcaj-terraform`.
- Đã đọc code, Terraform, script kiểm thử và hướng dẫn áp dụng; không tìm thấy
  AGENTS.md trên các đường dẫn áp dụng. Git ban đầu vẫn có workshop untracked;
  git diff trống không có nghĩa là không có file. Không ghi đè thay đổi có sẵn.
- STS trong sandbox gặp proxy `http://127.0.0.1:9`; chạy lại ngoài sandbox
  thành công. Đây là lỗi môi trường, không phải lỗi ứng dụng.

## Tài nguyên đã triển khai (setup ban đầu chờ xác nhận)

| Tài nguyên Terraform | Tên |
|---|---|
| `aws_sns_topic.monitoring_alerts` | `fcaj-ws04-Web_monitoring-alerts`, Standard |
| `aws_sns_topic_policy.monitoring_alerts` | Chính sách trên topic ở trên |
| `aws_sns_topic_subscription.monitoring_email` | Email endpoint được che trong evidence |
| `aws_cloudwatch_metric_alarm.availability` | `fcaj-ws04-Web_monitoring-availability-demo` |

- Plan trước apply: **4 create, 0 thay đổi tài nguyên cũ, 0 destroy**.
- Đã xác minh API: topic policy cho `cloudwatch.amazonaws.com` thực hiện
  `sns:Publish` trên đúng topic, giới hạn SourceAccount và SourceArn alarm.
  Statement quản trị topic giới hạn principal là account owner.
- ARN alarm tính từ tên cố định để policy không phụ thuộc resource alarm;
  alarm phụ thuộc policy, không tạo vòng dependency.
- Alarm: Availability / FCAJ/WebsiteMonitoring / MonitorId=ws04-main;
  Minimum < 1, period 60, evaluation 1/1, unit None, missing=`missing`.
  ALARM và OK gửi SNS; INSUFFICIENT_DATA không có action.
- Đây là cấu hình demo. Scheduler mỗi 5 phút nên dữ liệu thưa; missing không
  có nghĩa website khỏe. Alarm này chưa phát hiện monitor ngừng hoạt động.

**Setup ban đầu:** AWS báo `PENDING_CONFIRMATION`, nên chưa chạy kiểm thử lúc đó.
Sau đó người dùng xác nhận đã bấm Confirm; AWS API cũng báo confirmed trước
khi bắt đầu end-to-end. Không mở mailbox hoặc lưu/truy cập link xác nhận/unsubscribe.

## End-to-end đã hoàn tất sau xác nhận

Tất cả thời gian dưới đây là **30/10/2026, Asia/Saigon**. Mỗi pha invoke đúng
một lần, tổng cộng ba lần; chỉ đọc/poll trong lúc chờ, không tạo dữ liệu giả.

| Pha | Thời gian kết quả Lambda | HTTP | Availability | Alarm cập nhật |
|---|---|---|---|---|
| Baseline | 14:31:20 | 200 | 1 | OK, 14:32:40 |
| Lỗi | 14:33:18 | 503 | 0 | ALARM, 14:34:40 |
| Phục hồi | 14:35:12 | 200 | 1 | OK, 14:36:40 |

- Datapoint thuộc ba period khác nhau: **14:31, 14:33, 14:35**, mỗi period
  SampleCount=1, Minimum/Average/Maximum lần lượt bằng 1, 0, 1.
- Request_id baseline: `3cbfcc3b-9ac7-401f-84b8-bffcd5e48238`;
  lỗi: `8075cd9e-663e-4583-92d6-7101f34930b6`;
  phục hồi: `a23cfcce-b2f6-42f4-bb43-bd01b6452ae9`.
  Log JSON khớp toàn bộ response cho cả ba request.
- StateReason chỉ rõ mẫu 0 lúc 14:33 gây ALARM; mẫu 1 lúc 14:35 gây phục hồi.
  History ghi INSUFFICIENT_DATA → OK → ALARM → OK và ba SNS actions thành công
  lúc 14:32:40.974, 14:34:40.990, 14:36:40.969.
- Người dùng **đã xác nhận qua chat nhận đủ email ALARM và OK phục hồi**,
  phân biệt với email OK baseline. Đây là xác nhận người dùng; agent không
  truy cập hộp thư hoặc kiểm chứng ảnh hai email.
- TARGET_URL đã khôi phục `https://example.com`; Scheduler **DISABLED và
  không đổi**; code Lambda giữ nguyên; final plan **không còn thay đổi**.
- Script [session08_e2e.py](../scripts/session08_e2e.py) kiểm tra plan chỉ đổi
  URL trước mỗi apply, khôi phục trong finally ngay cả khi lỗi/chờ hết hạn.
  Không SetAlarmState, SNS publish tay hoặc PutMetricData trực tiếp.
- Evidence end-to-end riêng:
  [session08-e2e-2026-10-30-mvunk7mw](../evidence/session08-e2e-2026-10-30-mvunk7mw/),
  [tổng hợp hoàn tất](../evidence/session08-e2e-2026-10-30-mvunk7mw/verified-completion-summary.json),
  [xác nhận nhận email](../evidence/session08-e2e-2026-10-30-mvunk7mw/email-receipt-confirmation.json),
  [alarm history toàn đợt](../evidence/session08-e2e-2026-10-30-mvunk7mw/alarm-history-all.json),
  [plan cuối](../evidence/session08-e2e-2026-10-30-mvunk7mw/final-plan-summary.json).
  Trong cùng thư mục có response/log/metric/alarm/history từng pha, status
  subscription đã che email, cùng tóm tắt plan đổi và khôi phục URL.
  `summary.json` giữ kết quả máy lúc chưa hỏi nhận email;
  `verified-completion-summary.json` bổ sung xác nhận người dùng.
- Chưa kiểm chứng độ ổn định dài hạn, lỗi phát metric thực tế hoặc monitor
  ngừng chạy. Khi không còn dữ liệu mới vì Scheduler tắt, alarm có thể quay
  về INSUFFICIENT_DATA; không diễn giải đó thành website khỏe.

Mở email “AWS Notification - Subscription Confirmation”, đối chiếu tên topic
ở trên và bấm Confirm subscription. Kiểm tra Spam nếu chưa thấy; không gửi link
đó vào chat. Provider hỗ trợ email ở mức một phần: pending subscription chưa
thể unsubscribe độc lập, cần lưu ý khi cleanup.

## Cấu hình được giữ nguyên và minh chứng

- Lúc kết thúc setup TARGET_URL vẫn `https://example.com`, chưa đổi; ở đợt
  end-to-end sau đó đã tạm đổi và khôi phục đúng URL này.
- Scheduler **DISABLED, không đổi**; code/runtime/quyền Lambda, retention giữ
  nguyên. Final plan **không còn thay đổi**.
- Terraform fmt/validate đạt. Không chạy lại test mock vì không sửa app/test.
- Email chỉ nằm trong `infra/alerts.auto.tfvars.json`, đã kiểm tra Git ignore
  trước khi tạo. Biến `alert_email` sensitive, không có default trong .tf.
  Sensitive không loại email khỏi state/saved plan; các file này được ignore
  và không xuất toàn bộ vào báo cáo.
- Evidence mới: [session08-2026-10-30-mvumze56](../evidence/session08-2026-10-30-mvumze56/), gồm
  [setup summary](../evidence/session08-2026-10-30-mvumze56/setup-summary.json),
  [subscription đã che email](../evidence/session08-2026-10-30-mvumze56/subscription-status-redacted.json),
  [alarm API](../evidence/session08-2026-10-30-mvumze56/alarm-created.json),
  [topic policy](../evidence/session08-2026-10-30-mvumze56/topic-policy.json),
  [plan cuối](../evidence/session08-2026-10-30-mvumze56/setup-final-plan-summary.json)
  và Scheduler cuối. Không ghi đè minh chứng cũ.
- File mới: `infra/alarms-sns.tf`, `scripts/session08_setup.py`, nhật ký này,
  thư mục evidence và file email local ignored. Script setup chỉ tạo tài nguyên,
  không invoke hoặc thử gửi SNS message thủ công.

## Quy trình kiểm thử sau xác nhận (đã thực hiện)

1. Đọc lại trạng thái subscription; khi confirmed, invoke URL bình thường một
   lần để thiết lập OK, lưu response/log/metric và history.
2. Dùng Terraform đổi duy nhất TARGET_URL sang `https://httpbin.org/status/503`
   (đã kiểm chứng ở session 05), xem plan rồi apply. Invoke một lần trong
   period 60 giây khác baseline, xác minh 503/Availability=0 và chờ ALARM.
3. Luôn khôi phục URL ban đầu bằng plan chỉ đổi TARGET_URL, kể cả bước lỗi
   thất bại. Invoke phục hồi trong period khác pha 503 để Minimum=0 cũ không
   che kết quả 200/Availability=1, chờ OK.
4. Dựa vào timestamp/datapoint thực tế và SampleCount, không chỉ sleep cố định.
   Polling giới hạn khoảng 10 phút mỗi lần chờ alarm; không giữ URL lỗi để
   chờ email. Không SetAlarmState, SNS publish tay hoặc PutMetricData trực tiếp.

Phân biệt ba mức bằng chứng: (1) response/log/datapoint thật, (2) alarm state
và SNS action history, (3) email tới hộp thư do người dùng xác nhận/ảnh.
SNS action success không chứng minh email đã tới.
Chụp hai email ALARM và OK phục hồi; che địa chỉ cùng link xác nhận/unsubscribe.
Email OK baseline không được nhầm thành email phục hồi sau ALARM.

## Cleanup và chi phí

Hướng dẫn cleanup tập trung sau tổng kết: [docs/cleanup.md](cleanup.md).

Đã bổ sung hướng dẫn alarm/subscription/topic vào phần cleanup của
[session 07](session-07-metrics-dashboard.md). Chưa thực hiện cleanup.
Alarm, SNS và các dịch vụ liên quan có thể phát sinh chi phí; không khẳng định
miễn phí hoặc credit chi trả. Không commit/push.

## Tham khảo

- [AWS — alarm notifications và SNS policy](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Notify_Users_Alarm_Changes.html)
- [HashiCorp — email subscription/pending confirmation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic_subscription)
