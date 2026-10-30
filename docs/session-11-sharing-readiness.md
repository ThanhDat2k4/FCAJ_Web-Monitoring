# Session 11 — Chuẩn bị bản chia sẻ local

- Ngày 30/10/2026, Asia/Saigon. Chỉ thao tác local: không gọi AWS, chạy script
  tích hợp, apply/destroy, gửi email, cleanup, commit/push hoặc upload.
- Đọc hướng dẫn áp dụng, Git và tài liệu session 09–10. Không tìm thấy AGENTS.md.
  Git ban đầu có workshop untracked, chưa cấu hình remote; không đổi remote.
- Nguồn và evidence gốc được giữ nguyên; tài liệu mới là project-summary,
  nhật ký này và công cụ đóng gói local. Không sửa app/Terraform.

## Rà soát ảnh và nội dung

Đã mở xem đủ **12 PNG** trong evidence; SVG kiến trúc được kiểm tra XML/nhãn và
đối chiếu với bản PNG đã xem. Không thấy email cá nhân, credentials/token,
link xác nhận/unsubscribe hoặc tab cá nhân trong các vùng ảnh hiện có.
Từng file có phân loại trong image-review.json của evidence session 11.

Một số ảnh chứa Account ID/ARN, workspace path và tên tài nguyên. Bản xuất giữ
nguyên metadata này, không gọi chúng là credentials và không thay Account ID
trong Terraform. Không dùng ảnh danh sách email làm bằng chứng nội dung đầy đủ
hoặc request_id. Các ảnh cũ là snapshot lịch sử, không chứng minh trạng thái AWS
hiện tại. Không redaction/chỉnh sửa pixel hoặc tái tạo ảnh.

## Chính sách gói chia sẻ

- Allowlist: README, docs Markdown, source/test Python, Terraform .tf và lock
  file, script Python đã rà soát, evidence có phần mở rộng được chấp nhận và
  toàn bộ ảnh trong danh sách đã xem. Có manifest ghi rõ từng file/nguồn/hash.
- Loại state/backup/saved plans, .terraform, tfvars/email, .env/credentials/key,
  deployment ZIP, .git, cache, browser profile/snapshots/logs và output tạm.
- Script session05–08 có thể apply/invoke AWS, không thuộc test offline. Giữ
  trong gói để đối chiếu lịch sử; SHARE-NOTES trong bản xuất nhắc không chạy
  hàng loạt hoặc tái dùng plan/hash lịch sử. Script review/packaging chỉ local.
- Bản xuất có .gitignore độc lập và SHARE-NOTES được tạo mới. Chỉ sửa lệnh
  đường dẫn workspace trong README bản xuất cho phù hợp thư mục đã giải nén;
  code, Terraform và evidence vẫn giữ byte gốc. Không chỉnh sửa nguồn gốc.
- Không tự chọn license hoặc khẳng định quyền tái sử dụng ảnh/tài liệu của bên
  thứ ba. Người dùng quyết định giấy phép/phạm vi công khai trước khi publish.

## Bản xuất và cách đọc kết quả

Gói nằm dưới thư mục local Git-ignored
`output/share/session11-2026-10-30-mvurgzuq/`:

- `WS04-share/`: cây dự án chia sẻ.
- `WS04-share.zip`: archive local, chưa upload.
- `WS04-share/MANIFEST.json`: allowlist thực tế, kích thước và SHA-256 từng file.
- `WS04-share/PACKAGE-VERIFICATION.json`: test/link/privacy/image/archive checks.
- `WS04-share/SHA256SUMS.txt`: hash các file, bao gồm manifest.
- `WS04-share.zip.sha256`: hash chính ZIP.

Đường dẫn output này chỉ tồn tại ở bản nguồn; output không được lồng lại vào
ZIP. Trong bản đã giải nén, mở MANIFEST và PACKAGE-VERIFICATION ở thư mục gốc.
Kết quả chỉ được coi đạt khi báo cáo có test exit_code=0, không link thiếu,
không finding riêng tư còn lại và archive hash verification thành công.

Manifest và SHA256SUMS không tự hash chính mình để tránh vòng tự tham chiếu;
ZIP được kiểm tra riêng. Không coi checksum là chữ ký hoặc chứng nhận không
có bí mật. Kết quả đóng gói cuối được lưu riêng trong evidence session 11.

## Giới hạn trước khi công khai

Rà soát text là heuristic, ảnh được xem bằng mắt, không bảo đảm an toàn tuyệt
đối. Chưa kiểm tra GitHub preview hoặc publish. Chưa tự quyết định license,
chưa kiểm chứng deployment từ bản clone mới vì chặng này không gọi AWS.
Test chỉ chạy mock trên bản xuất; không chạy script integration.

[Project summary](project-summary.md), [README](../README.md) và
[mục lục evidence](evidence-index.md) mô tả đúng giới hạn bằng chứng.
Nếu bổ sung file/ảnh sau đóng gói, cần rà soát và tạo manifest/ZIP mới.
