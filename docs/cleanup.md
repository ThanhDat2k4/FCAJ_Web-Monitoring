# Cleanup WS04

Tài liệu này **chưa được thực thi** trong chặng 9. Không chạy cleanup nếu chỉ
muốn đọc báo cáo. Các lệnh apply bên dưới thay đổi/xóa tài nguyên thật, chỉ dùng
khi người dùng quyết định dọn đúng phạm vi và đã xem saved plan.

## Chuẩn bị chung

1. Giữ TARGET_URL ban đầu, Scheduler DISABLED; xác minh STS đúng Account
   `244477277232`, provider Region `ap-southeast-1`, profile `fcaj-terraform`.
2. Bảo toàn evidence đã che dữ liệu riêng tư. Log retention chỉ 1 ngày: lưu
   minh chứng cần thiết trước khi log hết hạn hoặc xóa log group.
3. Giữ đúng state, lock file và tfvars local. Không xóa state trước tài nguyên,
   không dùng `state rm` để giả vờ tài nguyên đã được dọn ở AWS.
4. Từ `infra`, chạy `terraform state list` để xem địa chỉ, không xuất toàn bộ
   state. Saved plans/state có thể chứa email dù biến sensitive: không chia sẻ.

## Chỉ tạm dừng hoạt động

Giữ `scheduler_enabled=false`. Khi cần đổi từ enabled:

```powershell
terraform plan "-var=scheduler_enabled=false" "-out=pause-review.tfplan"
# Xem plan: chỉ được đổi state của schedule.
terraform apply "pause-review.tfplan"
```

Kiểm tra AWS báo DISABLED, plan không có drift. Điều này giữ tài nguyên và
dữ liệu cũ, không bảo đảm chi phí bằng 0. Manual invocation vẫn phát metrics;
alarm vẫn đánh giá dữ liệu và có thể INSUFFICIENT_DATA khi không có mẫu.

## Dọn riêng phần cảnh báo

Không dùng `terraform destroy` cho cả module nếu vẫn muốn giữ Lambda/dashboard.
Tạo thay đổi cấu hình có thể review, theo thứ tự:

1. Gỡ resource `aws_cloudwatch_metric_alarm.availability` và output
   `monitoring_alarm_name`, xem plan và apply chỉ để dừng alarm/actions.
2. Với subscription confirmed, gỡ `aws_sns_topic_subscription.monitoring_email`,
   xem plan rồi apply để unsubscribe trước khi xóa topic.
3. Gỡ `aws_sns_topic_policy.monitoring_alerts`, `aws_sns_topic.monitoring_alerts`,
   output `monitoring_alert_topic_arn` và khai báo còn lại chỉ dành cho alarm/SNS.
   Xem plan rồi apply trong phạm vi đó, giữ nguyên tài nguyên các chặng trước.

Mỗi bước dùng saved plan mới, ví dụ `terraform plan "-out=alerts-cleanup.tfplan"`,
đọc rõ tài nguyên bị xóa rồi mới `terraform apply "alerts-cleanup.tfplan"`.
Không dùng `-target` để che các thay đổi ngoài phạm vi.

Pending subscription không thể unsubscribe độc lập. Nếu chưa confirmed, báo
đúng trạng thái và chọn cleanup topic có chủ đích; xóa topic làm các subscription
liên quan bị xóa bất đồng bộ. Xóa record khỏi state không phải bằng chứng AWS
đã xóa subscription. Không cần dùng/lưu link unsubscribe trong cleanup.

## Ngừng phát metrics hoặc dọn dashboard riêng

- Chỉ xóa dashboard: gỡ `aws_cloudwatch_dashboard.monitoring` và output URL,
  xem/apply plan chỉ xóa dashboard. Lambda vẫn phát metrics sau thao tác này.
- Ngừng phát metrics: trước tiên triển khai code ngừng gọi publish metrics;
  sau đó mới gỡ policy `monitoring_metrics` và dependency trong Lambda.
  Gỡ quyền khi code vẫn gọi SDK sẽ làm invocation thất bại.
- Gỡ locals chỉ khi không còn tham chiếu. Không xóa cấu hình code/dashboard
  hàng loạt khi alarm còn phụ thuộc metric đó mà chưa xem xét tác động.
- Không có lệnh xóa trực tiếp custom metric; ngừng phát không xóa ngay dữ liệu
  lịch sử, dữ liệu hết hạn theo retention của CloudWatch.

## Dọn toàn bộ WS04 khi kết thúc workshop

Chỉ dùng nếu người dùng muốn xóa cả Lambda, log group, hai IAM roles/policies,
Scheduler/group, dashboard, alarm, subscription và topic/policy của module này.
Không xóa tài nguyên ngoài module hoặc các workshop khác.

```powershell
terraform plan -destroy "-out=ws04-destroy-review.tfplan"
# Dừng tại đây để đọc/duyệt toàn bộ tài nguyên bị xóa.
# Chỉ sau quyết định cleanup thật:
terraform apply "ws04-destroy-review.tfplan"
```

Không dùng saved destroy plan cũ. Terraform xử lý thứ tự phụ thuộc; subscription
confirmed có thể unsubscribe trước topic. Sau apply, kiểm tra `terraform state
list` và AWS API/Console để xác nhận các tài nguyên dự định không còn tồn tại;
không kết luận sạch chỉ vì lệnh kết thúc hoặc state trống. Custom metric history
có thể còn hiển thị dù các producer/dashboard đã xóa.

Chỉ dọn file email local khi cấu hình không còn yêu cầu nó. Giữ state/backup
riêng tư trong thời gian cần đối chiếu; không đưa chúng vào commit/evidence.
Không tự xóa dữ liệu local hoặc minh chứng lịch sử trong chặng tổng kết.

## Tham khảo

- [HashiCorp — plan và destroy mode](https://developer.hashicorp.com/terraform/cli/commands/plan)
- [HashiCorp — destroy](https://developer.hashicorp.com/terraform/cli/commands/destroy)
- [AWS — xóa SNS topic/subscription](https://docs.aws.amazon.com/sns/latest/dg/sns-delete-subscription-topic.html)
- [AWS — metric lifecycle](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)
