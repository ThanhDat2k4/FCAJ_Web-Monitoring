# Session 09 — Tổng kết và chuẩn bị chia sẻ

- Ngày 30/10/2026 (Asia/Saigon). Chỉ đọc AWS, kiểm tra local và viết tài liệu;
  không apply/destroy, bật Scheduler, invoke Lambda, gửi email hoặc commit/push.
- Đã đọc Terraform/Python/test, script thực nghiệm, các bản verified và nhật ký.
  Không tìm thấy AGENTS.md áp dụng. Git ban đầu có `.gitignore` và workshop
  untracked; không dùng git diff trống để kết luận mọi file đã được theo dõi.

## Kết quả đã kiểm chứng

| Nội dung | Kết quả |
|---|---|
| Test local | 7/7 đạt, không gọi HTTP/AWS thật |
| HTTP thật | Đã kiểm chứng 503 → phục hồi 200 và log khớp request_id |
| Scheduler | Hai request khác nhau, metrics và thời điểm phù hợp lịch; nguồn gọi là suy luận, app chưa log trigger |
| Metrics | Availability/Latency có datapoint thật, đúng namespace/dimension |
| Dashboard | Cấu hình/API đã kiểm tra, chưa kiểm chứng UI Console |
| End-to-end | 200 → 503 → 200, Availability 1 → 0 → 1, OK → ALARM → OK, SNS actions thành công |
| Email | Người dùng xác nhận nhận ALARM/OK phục hồi; ảnh danh sách tiêu đề bổ trợ, không phải nội dung thư đầy đủ |

Nguồn và giới hạn từng kết quả ở [mục lục evidence](evidence-index.md).
Không biến kết quả thực nghiệm ngắn thành cam kết uptime hay chịu lỗi dài hạn.
Lỗi publish metric mới kiểm tra bằng mock, chưa fault injection AWS.
Chưa kiểm chứng monitor ngừng chạy; alarm demo hiện không xử lý tình huống đó.

## Trạng thái AWS ở chặng tổng kết

- STS đúng Account `244477277232`, provider/ARN đúng `ap-southeast-1`.
- Scheduler `DISABLED`; TARGET_URL `https://example.com`; runtime Python 3.13.
- Subscription confirmed. Alarm đã trở về `INSUFFICIENT_DATA` sau khi không có
  mẫu mới; trạng thái này không phủ nhận lần OK phục hồi trong history.
- Terraform plan chỉ đọc không có thay đổi. Không sửa file Terraform hoặc app.
- Snapshot và kiểm tra local được lưu trong thư mục evidence session 09,
  liên kết ở mục lục. Phiên bản local: Python 3.14.7, Terraform 1.16.1.

## Kiểm tra cuối chặng 9

- Test local 7/7 đạt; fmt/validate đạt; plan chỉ đọc exit_code=0, không có drift.
- Review cuối kiểm tra **113 file text**, parse 8 file Python, kiểm tra tĩnh
  1 block Mermaid và link Markdown nội bộ: không có finding còn lại.
- 10 nhóm đường dẫn kiểm tra Git ignore đều đạt: state/backup/plan, .terraform,
  email tfvars/tfvars, .env, private key và ZIP triển khai. Không mở file ignored.
- Review đầu được giữ nguyên: có 3 link tới các báo cáo/snapshot chưa được
  tạo lúc kiểm tra. Sau khi tạo artifact và xử lý link báo cáo tự tham chiếu,
  review cuối không còn link thiếu; không thay evidence cũ bằng kết quả mới.
- Tool review xử lý UTF-8 và UTF-16 BOM của log PowerShell. Không in nội dung
  khớp khi scan; ảnh/binary và các URL ngoài dự án không được kiểm tra tự động.
- Các thay đổi chặng này: README, evidence-index, cleanup, nhật ký này,
  script review local, link/tựa đề trong session 07/08 và evidence mới.
  Không sửa .tf, app.py, test, cấu hình email hoặc thực hiện cleanup thật.

## Thay đổi tài liệu

- Thêm [README](../README.md): kiến trúc Mermaid, cách triển khai có review,
  cấu hình email local, test, Scheduler/dashboard và giới hạn.
- Thêm [cleanup tập trung](cleanup.md): tạm dừng, dọn riêng cảnh báo,
  dọn dashboard/metrics và dọn toàn module. Chưa chạy cleanup/destroy plan.
- Thêm [mục lục evidence](evidence-index.md), nhật ký này và script review local.
- Giữ kết quả/ảnh cũ; thêm bản sao ảnh tiêu đề email mới sau kiểm tra bằng mắt.
- Bổ sung link tài liệu tập trung vào session 07/08, không viết lại minh chứng
  cũ thành kết quả mới.

## Trước khi chia sẻ

- Dùng danh sách file ứng viên từ Git (kể cả untracked, bỏ ignored). Kiểm tra
  file text bằng heuristic; chỉ ghi path/loại lỗi, không in nội dung khớp.
- State/backup/plan, .terraform, tfvars email, .env, key và ZIP triển khai
  phải được Git ignore. Không mở credentials hoặc state trong quá trình scan.
- Không coi kết quả scan là chứng nhận không có bí mật. Ảnh cũ/binary cần
  xem thủ công trước khi chia sẻ; rà soát lại nếu có file mới.
- Account ID/ARN không phải credentials nhưng là metadata môi trường.
  Có thể dùng placeholder trong bản xuất public; giữ nguyên evidence gốc và
  ghi rõ phần đã thay thế. Không chia sẻ file email hoặc link unsubscribe.
- Repo chưa commit/push; người dùng cần xem lại tập file định chia sẻ,
  hoàn thiện ảnh Console dashboard nếu muốn chứng minh UI, rồi mới tự quyết
  định công bố. Không tự hứa chi phí miễn phí hoặc được credit chi trả.

Sơ đồ Mermaid mới được kiểm tra tĩnh cho cú pháp đơn giản trong README;
chưa render bằng Mermaid CLI hoặc kiểm tra trên GitHub/VS Code preview.
Cleanup đã có hướng dẫn có thể review, chưa thực thi hoặc kiểm chứng xóa AWS.
