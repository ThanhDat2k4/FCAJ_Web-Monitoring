# Session 06 — EventBridge Scheduler gọi Lambda

- Ngày: 2026-10-30 (Asia/Saigon).
- Account: `244477277232`; Region: `ap-southeast-1`; profile: `fcaj-terraform`.
- Mục tiêu: triển khai lịch gọi Lambda hiện có, quan sát hai lần chạy rồi tắt.
- Đã đọc cấu hình thực tế và hướng dẫn áp dụng; không tìm thấy AGENTS.md trên
  các đường dẫn áp dụng. Git ban đầu có workshop untracked nên git diff trống
  không có nghĩa là thư mục không chứa file. Không ghi đè file người dùng.
- Plan ban đầu không có thay đổi; fmt/validate sau bổ sung cấu hình đều đạt.

## Tài nguyên mới

| Terraform resource | Tên trên AWS |
|---|---|
| `aws_scheduler_schedule_group.monitoring` | `fcaj-ws04-Web_monitoring` |
| `aws_scheduler_schedule.monitoring` | `fcaj-ws04-Web_monitoring-every-5-minutes` |
| `aws_iam_role.monitoring_scheduler` | `fcaj-ws04-Web_monitoring-scheduler-role` |
| `aws_iam_role_policy.monitoring_scheduler_invoke` | `fcaj-ws04-Web_monitoring-invoke-lambda` |

Scheduler role cho phép dịch vụ Scheduler gọi Lambda; Lambda role hiện có cho
phép code trong hàm ghi log khi chạy. Không sửa Lambda role hoặc logging policy.
Trust giới hạn principal `scheduler.amazonaws.com`, SourceAccount đúng account,
SourceArn đúng ARN **schedule group**. Policy chỉ cho `lambda:InvokeFunction`
trên ARN `aws_lambda_function.monitoring`, không dùng Resource `*`.

Cấu hình trong [scheduler.tf](../infra/scheduler.tf): `rate(5 minutes)`, timezone
UTC, flexible window OFF, input `{"trigger":"scheduler"}`, tối đa 2 retry và
event age 300 giây. `scheduler_enabled` mặc định false. Chu kỳ 5 phút dễ quan sát
trong lab mà vẫn hạn chế số lần gọi; OFF không có nghĩa là chính xác từng giây.

## Kết quả thực tế và minh chứng

- Yêu cầu bật lúc **11:45:03**, AWS xác nhận ENABLED lúc **11:45:14**;
  kết thúc quan sát lúc **11:51:04**, xác nhận DISABLED lúc **11:51:32**.
  Tất cả mốc giờ là ngày 30/10/2026, Asia/Saigon.
- Quan sát hai request_id khác nhau, không invoke thủ công trong thực nghiệm:

| Giờ Việt Nam | request_id | HTTP | healthy | error |
|---|---|---|---|---|
| 11:45:47 | `1c6ae420-d2c0-43f6-9096-37d39ae5bdc4` | 200 | true | null |
| 11:50:37 | `1c6ae421-fec0-43f6-9096-37d39ae5bdc4` | 200 | true | null |

- Hai log cách nhau khoảng **290 giây**, phù hợp chu kỳ 300 giây với độ chính
  xác lịch ở mức một phút. Cả hai kiểm tra `https://example.com`.
- Metrics trong cùng khoảng: AWS/Scheduler InvocationAttemptCount **2** theo
  ScheduleGroup; AWS/Lambda Invocations **2**, Errors **0** theo FunctionName.
  Các datapoint nằm ở phút 11:45 và 11:50. TargetErrorCount chưa có datapoint,
  không diễn giải danh sách rỗng thành bằng chứng không có lỗi.
- Cuối buổi: **DISABLED**, Lambda configuration giữ nguyên, Terraform plan
  **không còn thay đổi**. Không xóa tài nguyên, không commit/push.
- Minh chứng mới tại [session06-2026-10-30-mvuhi2hf](../evidence/session06-2026-10-30-mvuhi2hf/):
  [schedule khi bật](../evidence/session06-2026-10-30-mvuhi2hf/schedule-enabled.json),
  [schedule sau khi tắt](../evidence/session06-2026-10-30-mvuhi2hf/schedule-final-disabled.json),
  [log gốc của hai lần chạy](../evidence/session06-2026-10-30-mvuhi2hf/observed-logs.json),
  [metrics](../evidence/session06-2026-10-30-mvuhi2hf/metrics.json),
  [plan cuối](../evidence/session06-2026-10-30-mvuhi2hf/final-plan-summary.json),
  [tổng hợp](../evidence/session06-2026-10-30-mvuhi2hf/summary.json).
  Thư mục còn chứa cấu hình IAM/group, thời điểm bật và tóm tắt các plan.
- Thêm mới `infra/scheduler.tf`, `scripts/session06_scheduler.py`, nhật ký này
  và thư mục evidence riêng. Terraform tự cập nhật state/backup và sinh saved
  plans trong infra (Git ignore); giữ nguyên code ứng dụng và minh chứng cũ.
- STS trong sandbox bị lỗi proxy `http://127.0.0.1:9`; chạy lại ngoài sandbox
  theo cơ chế cấp quyền thành công. Không coi đây là lỗi ứng dụng.

## Quy trình và giới hạn bằng chứng

- Plan tạo chỉ thêm đúng bốn tài nguyên ở trên, schedule ban đầu DISABLED.
- Mỗi plan bật/tắt được kiểm tra trong bộ nhớ: chỉ update state của schedule,
  không thêm/xóa/thay thế tài nguyên hoặc thay đổi Lambda.
- [Script session06](../scripts/session06_scheduler.py) dùng helper CLI của
  session05, không gọi thủ công Lambda; tắt bằng Terraform trong finally.
  Script từ chối plan ngoài phạm vi, không lưu toàn bộ plan JSON/state.
- Log trực tiếp chứng minh request_id, thời điểm và kết quả HTTP của từng lần
  chạy. Quy nguồn Scheduler dựa thêm vào lịch đang bật, khoảng thời gian,
  metrics nếu có và việc thực nghiệm không invoke thủ công.
- Ứng dụng chưa ghi trường trigger; input cấu hình không chứng minh trường đó
  xuất hiện trong log. Không sửa mã ứng dụng để thêm trường này.
- Retry của Scheduler áp dụng cho giao nhận/gọi target. Cấu hình retry không
  phải minh chứng xử lý website lỗi: HTTP 503 có thể được app ghi thành kết quả
  unhealthy mà Lambda vẫn thực thi thành công. Chặng này không thử retry lỗi.
- Metrics sẵn có là bằng chứng bổ trợ; datapoint có thể đến chậm hoặc thiếu,
  không suy diễn tập datapoint rỗng thành số lỗi bằng 0.
- Chưa kiểm chứng retry khi giao nhận lỗi, độ ổn định dài hạn hoặc xác thực
  nguồn gọi cho từng request qua trường trigger. Không triển khai custom metrics,
  dashboard, SNS, alarm hoặc DLQ.

## Bật/tắt lại

Chạy trong `ws04-Web_monitoring\infra`, đọc plan trước mỗi apply. Chỉ tiếp tục
nếu plan cập nhật state của schedule, không có thay đổi ngoài dự kiến.

```powershell
terraform plan "-var=scheduler_enabled=true" "-out=scheduler-enable.tfplan"
terraform apply "scheduler-enable.tfplan"
```

Tắt sau khi thực hành:

```powershell
terraform plan "-var=scheduler_enabled=false" "-out=scheduler-disable.tfplan"
terraform apply "scheduler-disable.tfplan"
terraform plan "-var=scheduler_enabled=false"
```

## Ảnh Console nên chụp

1. Scheduler: schedule DISABLED, chu kỳ 5 phút và target Lambda đúng tên.
2. CloudWatch Logs: hai log website_check có request_id khác nhau, timestamp,
   http_status và is_healthy. Không cần thêm nhiều ảnh.

## Tham khảo

- [AWS — SourceArn phải là schedule group](https://docs.aws.amazon.com/scheduler/latest/UserGuide/cross-service-confused-deputy-prevention.html)
- [AWS — rate schedules và độ chính xác thời gian](https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html)
- [AWS — metrics Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/monitoring-cloudwatch.html)
- [HashiCorp — scheduler_schedule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/scheduler_schedule)
