# Session 13 — Chuẩn bị cleanup WS04

Ngày 31/10/2026, Asia/Saigon. **Đã cleanup sau khi người dùng duyệt saved plan:
14 tài nguyên bị xóa; AWS/state đã được kiểm tra.**

## Kết quả cleanup đã hoàn tất

- Người dùng duyệt: “Duyệt xóa 14 tài nguyên theo plan này”. Kiểm tra lại STS
  đúng Account `244477277232`, Region `ap-southeast-1`, Scheduler DISABLED.
- SHA-256 saved plan khớp chính xác
  `3d382fb7dc7979b1b41ed4f845d2032e60454efa8e277c93256bef63fbcef801`.
  Kiểm tra lại đủ 14 actions delete rồi apply đúng file đó; không lập plan
  thay thế hoặc xóa thủ công ngoài Terraform.
- Terraform apply exit 0, báo **14 destroyed**. State list exit 0 và không còn
  managed resource. Không dùng state rm để làm trống state.
- AWS API xác nhận không còn Lambda, log group, dashboard, alarm, hai IAM
  roles và ba inline policies, schedule/group, SNS topic/subscription.
  Topic policy được xác nhận gián tiếp bằng việc topic cha không còn tồn tại:
  tổng cộng 13 kiểm tra trực tiếp và 1 qua parent absence, đủ 14 resources.
- Bộ kiểm tra đầu ghi 13/14 do chưa nhận diện mã dashboard `ResourceNotFound`.
  Đọc lại GetDashboard trả “Dashboard ... does not exist”; bản verified bổ sung
  xác nhận cuối. Giữ nguyên kết quả trung gian, không coi đây là lỗi cleanup.

[Kết quả verified cuối](../evidence/session13-2026-10-31-mvweevxs/review-mvweibh6/execution/verified-completion.json),
[duyệt plan](../evidence/session13-2026-10-31-mvweevxs/review-mvweibh6/execution/approval.json),
[apply/state](../evidence/session13-2026-10-31-mvweevxs/review-mvweibh6/execution/apply-result.json),
[API absence ban đầu](../evidence/session13-2026-10-31-mvweevxs/review-mvweibh6/execution/aws-absence.json).

## Phần được giữ và giới hạn

- ZIP/evidence cũ kiểm tra lại hash vẫn khớp. Giữ source, Terraform, state hiện
  tại và các backup private, kể cả bản sao ngay trước apply. Raw apply log và
  saved plan chỉ nằm ở output Git-ignored; không đưa lên GitHub.
- Không thay repository GitHub, commit/push, profile hoặc IAM identity đăng
  nhập, không cleanup tài nguyên workshop khác. Không cần khôi phục URL hoặc
  bật/tắt Scheduler sau xóa: Lambda và schedule đã không còn tồn tại.
- Custom metrics lịch sử không được xóa trực tiếp; có thể còn hiển thị theo
  retention. Chưa kiểm chứng lịch sử metrics sau cleanup, billing cuối cùng
  hoặc chi phí toàn tài khoản bằng 0. Không bảo đảm miễn phí/credit chi trả.
- Cấu hình được giữ: một plan/apply thường trong tương lai có thể đề nghị tạo
  lại stack. Không chạy plan thường để gọi trạng thái đó là “không thay đổi”.
  Kết luận cleanup dựa trên state không còn managed resource và AWS absence.

Các phần bên dưới lưu diễn biến chuẩn bị **trước apply**, không phải trạng
thái hiện tại.

## Kết quả mới sau đăng nhập lại

- STS profile fcaj-terraform xác nhận Account `244477277232`. Provider và các
  API đọc dùng Region `ap-southeast-1`; Lambda ARN/target Scheduler khớp.
- Scheduler AWS **DISABLED**, TARGET_URL `https://example.com`.
- Plan thường có refresh: không có managed change, không resource drift.
  Refresh đã đối chiếu 14 managed resources trong state qua provider AWS.
- Destroy plan: **14 delete, 0 create/update/replace**, đúng tập địa chỉ managed
  trong state; không dùng tên prefix làm bằng chứng quyền xóa.
- Query CloudWatch website_check trả 0 event ở trang đã lấy. Không tạo dữ liệu
  thử hoặc khẳng định toàn bộ log đã hết hạn; xem cờ pagination trong evidence.
  Evidence lịch sử và ZIP đã kiểm tra hash vẫn giữ nguyên.
- Hash state gốc không đổi sau cả hai plan. Không xóa state/tfvars hoặc đổi code.

[Bảng actions và kết quả](../evidence/session13-2026-10-31-mvweevxs/review-mvweibh6/review-completed.json),
[AWS preflight](../evidence/session13-2026-10-31-mvweevxs/review-mvweibh6/aws-preflight.json),
[baseline summary](../evidence/session13-2026-10-31-mvweevxs/review-mvweibh6/baseline.tfplan.summary.json).
Các JSON này đã lọc, không chứa raw plan/state hoặc endpoint email subscription.

Saved destroy plan **private, gitignored**:

```text
output/cleanup/session13-2026-10-31-mvweevxs/review-mvweibh6/destroy.tfplan
SHA-256: 3d382fb7dc7979b1b41ed4f845d2032e60454efa8e277c93256bef63fbcef801
```

Chưa yêu cầu xóa ngoài stack; GitHub, profile đăng nhập và IAM identity dùng
Terraform không nằm trong plan. Plan/state chứa dữ liệu nhạy cảm, không đưa
file binary hoặc raw JSON lên GitHub. Chỉ apply đúng saved plan này sau duyệt;
nếu state/cấu hình thay đổi hoặc phải lập lại plan, trình khác biệt trước.

Phần thông báo credentials hết hạn bên dưới là lịch sử lần kiểm tra đầu;
trở ngại đăng nhập đã được giải quyết.

## Kiểm tra và trở ngại

- Đã đọc hướng dẫn áp dụng, Git, toàn bộ Terraform, cleanup và session12.
  Không tìm thấy AGENTS.md ở các vị trí đã kiểm tra. Git gốc vẫn có workshop
  untracked; không commit/push, đổi remote hoặc sửa code/Terraform.
- Provider dùng profile `fcaj-terraform`, Region `ap-southeast-1`, account guard
  `244477277232`. Đây là cấu hình local, **chưa xác minh được danh tính AWS**.
- STS trong sandbox lỗi kết nối AWS Sign-In; retry ngoài sandbox trả đúng lỗi:
  `Your session has expired. Please reauthenticate using 'aws login'.`
  Không coi lỗi môi trường/xác thực là lỗi ứng dụng.
- `terraform fmt -check`: đạt. Validate trong sandbox không khởi động được
  provider; retry ngoài sandbox: `Success! The configuration is valid.`
- Không dùng plan cũ hoặc `-refresh=false` để thay cho kiểm tra AWS hiện tại.
  Chưa xác minh Scheduler, TARGET_URL, tài nguyên tồn tại, drift hoặc log còn
  retention. Không bật schedule/invoke Lambda để tạo lại dữ liệu.

## Minh chứng và state đã bảo toàn

- ZIP chia sẻ chặng11 khớp checksum; 144 payload entries trong manifest khớp
  SHA-256. Gói vẫn có 146 file tính cả manifest/checksum; giữ nguyên bản gốc.
- Sao chép `terraform.tfstate` và `terraform.tfstate.backup` vào thư mục private
  `output/cleanup/session13-2026-10-31-mvweevxs/`. Kiểm tra byte/hash khớp,
  thư mục được gitignore. Không in nội dung state, không đưa state vào evidence
  chia sẻ hoặc GitHub. Gitignore không phải mã hóa hoặc bảo đảm kiểm soát truy cập.
- Giữ state/tfvars/lock hiện có; chưa xóa file local. Chưa lấy thêm log AWS vì
  credentials hết hạn; không khẳng định log đã hết hạn hay còn tồn tại.
- [Báo cáo chuẩn bị đã lọc](../evidence/session13-2026-10-31-mvweevxs/preparation-summary.json).

## Phạm vi 14 managed resources trong destroy plan (chờ duyệt)

`terraform state list` có 14 managed resources dưới đây. Plan mới có refresh
đã xác nhận đúng tập 14 địa chỉ này với action delete; chưa apply.

| Resource address | Loại |
|---|---|
| aws_cloudwatch_dashboard.monitoring | Dashboard |
| aws_cloudwatch_log_group.monitoring | Log group |
| aws_cloudwatch_metric_alarm.availability | Alarm |
| aws_iam_role.monitoring_lambda | Lambda execution role |
| aws_iam_role.monitoring_scheduler | Scheduler execution role |
| aws_iam_role_policy.monitoring_logs | Inline logging policy |
| aws_iam_role_policy.monitoring_metrics | Inline metrics policy |
| aws_iam_role_policy.monitoring_scheduler_invoke | Inline invoke policy |
| aws_lambda_function.monitoring | Lambda |
| aws_scheduler_schedule.monitoring | Schedule |
| aws_scheduler_schedule_group.monitoring | Schedule group |
| aws_sns_topic.monitoring_alerts | SNS topic |
| aws_sns_topic_policy.monitoring_alerts | SNS topic policy |
| aws_sns_topic_subscription.monitoring_email | Email subscription |

Ba data sources `archive_file.monitoring_lambda`, `aws_caller_identity.current`
và `aws_partition.current` không phải ba tài nguyên AWS được tạo thêm.
Không đưa IAM identity dùng Terraform, profile đăng nhập, workshop khác hoặc
repository GitHub vào phạm vi cleanup.

## Tác động cần duyệt sau khi có plan thật

Cleanup toàn stack sẽ ngừng checker/cảnh báo, xóa dashboard và log group cùng
log trong đó, gỡ subscription và các role/policy thuộc stack. Evidence local
và GitHub được giữ nguyên. Metrics lịch sử không bị xóa trực tiếp chỉ vì xóa
producer/dashboard. Không khẳng định toàn tài khoản ngừng phát sinh chi phí.

## Trình tự chuẩn bị và điểm chờ duyệt

1. Đã đăng nhập lại và xác minh STS bằng fcaj-terraform.
2. Đã đối chiếu AWS qua API và refresh; Scheduler DISABLED, không thấy drift.
3. Đã tạo saved destroy plan trong vùng private; đường dẫn/hash ở đầu nhật ký.
4. **Chưa apply** cho đến khi người dùng duyệt plan cụ thể. Nếu phải lập lại
   plan, so sánh và trình thay đổi. Sau apply mới kiểm tra AWS/state để kết luận.

Hiện chờ người dùng duyệt đúng 14 deletions theo plan/hash ở đầu nhật ký.
Chưa chạy AWS cleanup hoặc thay đổi GitHub; chưa kiểm chứng trạng thái sau xóa.
