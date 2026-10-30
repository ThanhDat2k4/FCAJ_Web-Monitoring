# WS04 — Website Monitoring: tóm tắt portfolio

## Bài toán

Tự động kiểm tra một website, lưu kết quả có thể đối chiếu, hiển thị trạng thái
và gửi email khi website lỗi/phục hồi. Dự án phục vụ học AWS/DevOps; không tuyên
bố uptime, chịu tải hoặc sẵn sàng production.

## Kiến trúc và công nghệ

EventBridge Scheduler gọi Lambda Python; Lambda thực hiện HTTP GET, ghi JSON
vào CloudWatch Logs và gửi Availability/Latency bằng một PutMetricData.
Dashboard hiển thị metrics. Alarm Availability gửi SNS email khi ALARM và OK.
Terraform quản lý IAM, Lambda, log group, Scheduler, dashboard và alarm/SNS.

- [Kiến trúc và hướng dẫn](../README.md).
- [Sơ đồ đã render](../evidence/session10-2026-10-30-mvuq082h/architecture.svg).
- [Dashboard Console thật](../evidence/session10-2026-10-30-mvuq082h/dashboard-widgets.png).

## Công việc và kết quả đã kiểm chứng

| Nội dung | Kết quả thực nghiệm |
|---|---|
| HTTP checker | HTTP 200 healthy; HTTP 503 unhealthy; có request_id đối chiếu response/log |
| Test offline | 7 test mock: HTTP/kết nối/timeout, metric payload và lỗi phát metric |
| Scheduler | Quan sát hai request khác nhau, thời gian và metrics phù hợp chu kỳ 5 phút |
| Custom metrics | Availability/Latency có datapoint AWS thật, dimension cố định MonitorId=ws04-main |
| Dashboard | Xem Console, đối chiếu API/period 300, dữ liệu và timezone; có ảnh thật |
| End-to-end | 200 → 503 → 200; Availability 1 → 0 → 1; OK → ALARM → OK; SNS actions thành công |
| Email | Người dùng xác nhận nhận ALARM và OK phục hồi; ảnh danh sách tiêu đề bổ trợ |

Các pha end-to-end ngày 30/10/2026 nằm ở ba phút khác nhau (14:31, 14:33,
14:35 giờ Việt Nam), tránh Minimum=0 cùng period che mẫu phục hồi.
[Mục lục minh chứng](evidence-index.md) phân biệt API/log, suy luận và xác nhận
người dùng, kèm các kết quả trung gian đã được khắc phục.

## Phân biệt lỗi website và lỗi hệ thống giám sát

HTTP 503 là kết quả kiểm tra: app ghi unhealthy, phát Availability=0 rồi có thể
kết thúc invocation thành công. Vì vậy Lambda Errors=0 không có nghĩa website
khỏe. Nếu PutMetricData thất bại, app ghi event riêng metrics_publish_error và
raise; lỗi SDK không bị ghi đè vào trường error của kết quả HTTP.
Nhánh lỗi publish đã kiểm tra bằng mock, chưa fault injection trên AWS.

## Bài học

- Tách Scheduler role gọi hàm khỏi Lambda execution role khi code chạy.
  Giới hạn trust/publish theo account và đúng ARN group/alarm; PutMetricData
  giới hạn namespace bằng IAM condition.
- Xem saved plan trước apply, dừng khi thay đổi ngoài phạm vi; luôn có đường
  khôi phục URL và tắt Scheduler sau thực nghiệm.
- Dùng request_id để đối chiếu response/log; metric không có request_id nên
  cần timestamp, giá trị và SampleCount để đánh giá tương quan.
- Missing data là chưa biết, không phải healthy. Period 300 của dashboard có
  thể gộp mẫu 1 và 0; Minimum=0 không chứng minh lỗi suốt 5 phút.
- Tách evidence thật khỏi mock, giữ kết quả trung gian và nêu cách sửa; SNS
  action success không tự chứng minh email tới hộp thư.

## Giới hạn và hướng cải tiến

Chưa kiểm chứng vận hành dài hạn, chịu tải, phục hồi khi AWS SDK lỗi thật hoặc
monitor ngừng phát dữ liệu. Scheduler attribution dựa vào cấu hình/thời gian/
metrics vì app chưa ghi trigger. Chưa có DLQ và alarm phát hiện missing monitor.

Có thể cân nhắc kiểm tra freshness của dữ liệu, thử lỗi giao nhận có kiểm soát,
CI cho test/validate và quản lý state phù hợp đội nhóm. Đây là hướng đề xuất,
chưa triển khai hoặc ghi nhận là đã đạt. Không đưa số liệu tiết kiệm chi phí
hay bảo đảm credit chi trả khi chưa có bằng chứng.

Trạng thái cuối đã xác minh ở session 10: Scheduler DISABLED, URL ban đầu được
giữ nguyên. Chặng chuẩn bị chia sẻ chỉ làm local, không xác minh lại AWS.
Cleanup là công việc riêng theo [hướng dẫn](cleanup.md), chưa thực hiện.
