# Session 10 — Kiểm chứng Console và render Mermaid

- Ngày: 30/10/2026, Asia/Saigon. Chỉ đọc AWS, thao tác bộ lọc hiển thị,
  render local và bổ sung tài liệu/evidence.
- Đã đọc README, Terraform dashboard, evidence-index, nhật ký và hướng dẫn
  áp dụng; không tìm thấy AGENTS.md. Không ghi đè thay đổi/evidence cũ.
- STS, ARN và Console cùng đúng Account `244477277232`, Region
  `ap-southeast-1`. Scheduler giữ **DISABLED**, TARGET_URL
  `https://example.com`; không invoke, apply, destroy, publish hoặc gửi email.

## Dashboard UI đã kiểm chứng

Agent dùng skill Playwright, mở Chrome riêng. Người dùng đăng nhập trực tiếp;
agent không đọc/xuất cookies, token, mật khẩu hoặc hồ sơ trình duyệt cá nhân.
Console hiển thị đúng account, Singapore và dashboard `fcaj-ws04-Web_monitoring`.

Khoảng tuyệt đối đã chọn trên Console: **30/10/2026 06:55–07:40 UTC**,
tương đương **13:55–14:40 Việt Nam**. Chỉ bấm Apply của bộ chọn Calendar;
**Autosave Off**, không bấm Save dashboard. Đối chiếu API sau thao tác cho thấy
dashboard body trùng bản session 07, không thay cấu hình lưu trên AWS.

| Widget | Đối chiếu UI với Terraform/API |
|---|---|
| Availability | Đã thấy điểm 1 lúc 07:00 UTC, bucket 07:30 ở 0, 07:35 ở 1; Minimum/300, Y 0–1 |
| HTTP request latency | Hai legend Average/Maximum, trục ms; period 300; dữ liệu khớp bảng bên dưới |
| Lambda Invocations/Errors | Đúng function theo API, Sum/300; ảnh thấy Invocations 1/2/1 và Errors 0 |
| Ghi chú | Có thông báo missing data không phải verified check, latency không phải tải toàn trang |

Nguồn custom metrics: `FCAJ/WebsiteMonitoring`, dimension duy nhất
`MonitorId=ws04-main`; native metrics: `AWS/Lambda`,
`FunctionName=fcaj-ws04-Web_monitoring`. Cấu hình namespace/dimension/statistic/
period được kiểm tra qua API, kết hợp quan sát UI thực tế, không chỉ đọc ảnh.

| Bucket (giờ Việt Nam) | Availability Min | SampleCount | Latency Avg / Max (ms) | Invocations / Errors Sum |
|---|---|---|---|---|
| 14:00 | 1 | 1 | 455,59 / 455,59 | 1 / 0 |
| 14:30 | 0 | 2 | 726,21 / 995,07 | 2 / 0 |
| 14:35 | 1 | 1 | 448,13 / 448,13 | 1 / 0 |

Bucket 14:30 gộp mẫu healthy ở 14:31 và unhealthy ở 14:33 nên Minimum=0;
không chứng minh website lỗi liên tục cả 5 phút. Đường nối không tạo thêm
sample hoặc chứng minh healthy giữa các điểm. Khoảng trống 14:05–14:25 không
được diễn giải thành website khỏe.

Lambda Errors=0 vẫn có thể đi cùng website HTTP 503: handler xử lý HTTPError,
phát Availability=0 rồi trả kết quả bình thường. Errors là lỗi thực thi Lambda,
không thay thế Availability để đánh giá website.

## Minh chứng mới

Thư mục [session10-2026-10-30-mvuq082h](../evidence/session10-2026-10-30-mvuq082h/):

- [Ảnh khoảng thời gian và UTC timezone](../evidence/session10-2026-10-30-mvuq082h/dashboard-time-range.png).
- [Ảnh toàn bộ widget](../evidence/session10-2026-10-30-mvuq082h/dashboard-widgets.png).
- [Dashboard API](../evidence/session10-2026-10-30-mvuq082h/dashboard-api.json) và
  [datapoint period 300](../evidence/session10-2026-10-30-mvuq082h/dashboard-data-300s.json).
- [Kiểm tra AWS cuối, chỉ đọc](../evidence/session10-2026-10-30-mvuq082h/aws-final-read-only.json).
- [Tổng hợp kiểm chứng](../evidence/session10-2026-10-30-mvuq082h/visual-verification.json).

Hai ảnh Console do agent chụp bằng browser automation, chọn riêng vùng DOM;
không sửa dữ liệu/cắt ghép tạo nội dung giả. Đã xem ảnh trước khi sao chép vào
evidence: không có email cá nhân, URL xác nhận/unsubscribe hoặc thanh tài khoản.
Ảnh không phải bằng chứng nhận email, không thay thế evidence session 08.

## Mermaid đã render thật

- Trích nguyên block Mermaid từ README vào
  [architecture.mmd](../evidence/session10-2026-10-30-mvuq082h/architecture.mmd), không đổi nội dung.
- Render bằng `@mermaid-js/mermaid-cli 12.0.0`, dùng Google Chrome đã cài,
  xuất [SVG](../evidence/session10-2026-10-30-mvuq082h/architecture.svg) và
  [PNG](../evidence/session10-2026-10-30-mvuq082h/architecture.png). Agent đã mở PNG kiểm tra bố cục,
  chữ và các nhánh kết nối; SVG có nội dung diagram thực.
- [Metadata render và SHA-256](../evidence/session10-2026-10-30-mvuq082h/mermaid-render.json) ghi nguồn,
  phiên bản và hash. Không thêm thành phần chưa triển khai.
- Lệnh thực tế dùng `mmdc -i <source.mmd> -o <artifact.svg|png>
  -p <local-puppeteer-config.json> --size 2400 -b white`.
  Config local chỉ định executablePath của Chrome; `PUPPETEER_SKIP_DOWNLOAD=1`
  để không tải thêm Chromium. Không thêm dependency production/global project.
- CLI bản này dùng `--size`, không nhận `-w`; đã đọc help rồi sửa lệnh render.
  Nếu tái hiện, chọn thư mục output mới và đường dẫn Chrome phù hợp máy.

## Lỗi môi trường và giới hạn còn lại

- npm sandbox không có package cached; Git Bash trong sandbox gặp signal pipe
  Win32 error 5. Chạy ngoài sandbox theo cơ chế cấp quyền khắc phục được.
- Output Unicode của snapshot gặp encoding Windows; in UTF-8/che email và URL.
  Lần click Apply đầu bị footer che, tăng viewport rồi click lại thành công.
  Một số thẻ main không có bounding box; chụp toolbar và grid thay vì main.
- File làm việc Playwright nằm dưới `output/` được Git ignore. Không copy
  browser snapshots/logs/auth state vào evidence chia sẻ.
- Chưa kiểm chứng mọi thao tác/settings của Console, render GitHub preview
  hoặc độ ổn định dài hạn. Mermaid đã render local, không còn chỉ kiểm tra tĩnh.
- Các giới hạn nghiệp vụ vẫn giữ: chưa phát hiện monitor ngừng chạy,
  Scheduler attribution dựa trên suy luận bổ trợ, chưa fault-inject publish
  metric trên AWS. Không chạy lại test/plan không cần thiết khi chỉ sửa tài liệu.
- Không cleanup, commit/push hoặc publish repository. Trước công khai vẫn cần
  xem thủ công các ảnh cũ và rà soát lại tập file định chia sẻ.

## Tham khảo

- Đã đọc skill local `playwright` trước khi dùng công cụ trình duyệt.
- [Playwright CLI](https://github.com/microsoft/playwright-cli)
- [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)
