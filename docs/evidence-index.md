# Mục lục minh chứng WS04

Các kết quả dưới đây là thực nghiệm ngày 29–30/10/2026, không phải trạng thái
website liên tục. Mỗi session có scope riêng; đọc bản tổng hợp cuối cùng cùng
nhật ký lỗi, không coi summary trung gian là kết quả sau khắc phục.

| Nhóm | Kết quả được chứng minh | Nguồn chính | Giới hạn |
|---|---|---|---|
| Test local | 7 tình huống mock đạt; metric payload và publish errors | [Test hiện tại](../evidence/session09-2026-10-30-mvuocnv1/local-tests.json), [source test](../tests/test_app.py) | Không phải request HTTP/AWS thật; local Python 3.14 khác runtime 3.13 |
| HTTP lỗi/phục hồi AWS | HTTP 503/unhealthy rồi 200/healthy, request_id khớp log | [Session 05 verified](../evidence/session05-2026-10-30-mvugznnk/verified-summary.json), [nhật ký](session-05-aws-failure-recovery.md) | Trước khi có custom metrics; không dùng kết quả này để khẳng định đã phát Availability=0 |
| Scheduler | Hai log khác request_id cách khoảng 290 giây; Scheduler/Lambda metrics cùng có 2 invocations | [Session 06 summary](../evidence/session06-2026-10-30-mvuhi2hf/summary.json), [log](../evidence/session06-2026-10-30-mvuhi2hf/observed-logs.json), [metrics](../evidence/session06-2026-10-30-mvuhi2hf/metrics.json) | Log không ghi trigger; quy nguồn Scheduler là suy luận có cấu hình/thời gian/metrics bổ trợ |
| Custom metrics | Một invocation HTTP 200; Availability=1, Latency=455.59 ms, SampleCount=1 | [Session 07 verified](../evidence/session07-2026-10-30-mvultcfx/verified-summary.json), [metrics](../evidence/session07-2026-10-30-mvultcfx/metrics.json) | Correlation bằng thời gian/giá trị/số mẫu, không có request_id trong dimension |
| Dashboard | API đúng cấu hình; chặng 10 đã xem Console thật, chọn thời gian tuyệt đối và đối chiếu biểu đồ period 300 | [API session 07](../evidence/session07-2026-10-30-mvultcfx/dashboard-api.json), [ảnh widgets](../evidence/session10-2026-10-30-mvuq082h/dashboard-widgets.png), [nhật ký chặng 10](session-10-visual-verification.md) | Chỉ kiểm chứng các widget/khoảng thời gian nêu trong nhật ký, không bảo đảm healthy giữa các điểm |
| Alarm/SNS setup | Tạo alarm, topic/policy/subscription; ban đầu pending confirmation | [Setup summary](../evidence/session08-2026-10-30-mvumze56/setup-summary.json), [policy](../evidence/session08-2026-10-30-mvumze56/topic-policy.json) | Setup summary là snapshot trước người dùng bấm Confirm |
| End-to-end | 200/503/200 → 1/0/1 ở ba phút riêng → OK/ALARM/OK; ba SNS actions success | [Hoàn tất session 08](../evidence/session08-e2e-2026-10-30-mvunk7mw/verified-completion-summary.json), [history](../evidence/session08-e2e-2026-10-30-mvunk7mw/alarm-history-all.json), [nhật ký](session-08-alarms-sns.md) | Action success chứng minh CloudWatch thực hiện action, không tự chứng minh email đến inbox |
| Email nhận thật | Người dùng xác nhận nhận ALARM và OK phục hồi; có ảnh hai tiêu đề email | [Xác nhận qua chat](../evidence/session08-e2e-2026-10-30-mvunk7mw/email-receipt-confirmation.json), [ảnh tiêu đề](../evidence/session09-2026-10-30-mvuocnv1/email-subjects.png) | Không truy cập mailbox tự động; ảnh danh sách không phải nội dung đầy đủ hay bằng chứng request_id |
| Mermaid | Đã render nguyên sơ đồ README thành SVG/PNG bằng Mermaid CLI 12.0.0, xem PNG thực tế | [SVG](../evidence/session10-2026-10-30-mvuq082h/architecture.svg), [PNG](../evidence/session10-2026-10-30-mvuq082h/architecture.png), [metadata](../evidence/session10-2026-10-30-mvuq082h/mermaid-render.json) | Render local, chưa kiểm tra GitHub preview; không thay thế ảnh Console |

## Cách đối chiếu request, metric và alarm

- Trong mỗi thư mục session 05/08, mở `*-response.json` và `*-log.json` hoặc
  `*-cloudwatch-confirmed.json`, so request_id và toàn bộ JSON website_check.
- Session 08: `baseline-metric.json`, `failure-metric.json`,
  `recovery-metric.json` có SampleCount=1 ở các phút 14:31, 14:33, 14:35
  (giờ Việt Nam). Metric không chứa request_id.
- `*-alarm.json` có StateReason/StateUpdatedTimestamp; `*-history.json` và
  history toàn đợt có chuyển trạng thái và SNS actions. ALARM lúc 14:34:40,
  OK phục hồi lúc 14:36:40, phân biệt OK baseline lúc 14:32:40.
- `summary.json` có thể là kết quả máy trước hỏi xác nhận email;
  `verified-completion-summary.json` bổ sung xác nhận của người dùng sau đó.

## Kết quả trung gian và tài liệu lịch sử

- Session 05 giữ `*-cloudwatch.json` rỗng của truy vấn UUID chưa đặt ngoặc kép.
  File `*-cloudwatch-confirmed.json` là kết quả truy vấn sửa cho cùng request;
  không gọi thêm Lambda để thay bằng chứng.
- Session 07 giữ summary ban đầu bị lỗi encoding khi so dashboard, chưa invoke.
  Bản verified được tạo sau khi sửa UTF-8 cho CLI rồi invoke đúng một lần.
- Session 03 nêu ảnh `03_lambda-cloudwatch-log.png` nhưng file không có trong
  workspace đã kiểm tra. Không tạo ảnh giả hoặc đánh dấu ảnh đó đã xác minh.
- Session 01/02 có trường mẫu/trạng thái cũ, tên tài nguyên cũ; giữ làm lịch sử.
  Trạng thái mới xem [README](../README.md) và các bản verified tương ứng.

## Bản rà soát chặng 9

Các giới hạn UI/render ở chặng 9 là snapshot lịch sử. Chặng 10 đã bổ sung
[Console và Mermaid render thực tế](session-10-visual-verification.md), không
viết lại các summary cũ thành kết quả mới.

- [Snapshot AWS chỉ đọc](../evidence/session09-2026-10-30-mvuocnv1/read-only-state.json).
- [Kết quả test local](../evidence/session09-2026-10-30-mvuocnv1/local-tests.json).
- [Rà soát cuối: link/ignore/dấu hiệu dữ liệu riêng tư](../evidence/session09-2026-10-30-mvuocnv1/local-review-final.json).
- [Kết quả fmt/validate/plan](../evidence/session09-2026-10-30-mvuocnv1/verification-summary.json).
- [Tổng kết và các giới hạn](session-09-project-wrap-up.md).

Ảnh email mới đã xem trực tiếp trước khi sao chép: không thấy email cá nhân,
link xác nhận/unsubscribe. Không sao chép ảnh trang xác nhận subscription có
link nhạy cảm. Các ảnh PNG cũ không được scan tự động; xem thủ công từng ảnh
trước khi xuất bản. Log retention chỉ 1 ngày, nên evidence local là snapshot
được bảo toàn, không bảo đảm có thể đọc lại cùng log trên AWS về sau.
