# Session 14 — Portfolio sau cleanup

Ngày 31/10/2026, Asia/Saigon. **Chuẩn bị diff local, chưa commit/push.**

## Kết quả thực tế

- Đọc hướng dẫn áp dụng, Git, README, project summary, session12–13 và evidence
  cleanup đã lọc. Không tìm thấy AGENTS.md trong phạm vi đã kiểm tra.
- Connector xác nhận `ThanhDat2k4/FCAJ_Web-Monitoring` Public, default branch main.
  Clone mới vào thư mục tạm ngoài Git workspace, HEAD
  `7c8b6d605603714305f56f07816351f154ad116a`, working tree ban đầu sạch.
- Chạy `python -B -m unittest discover -s tests -v` ngay từ clone mới trước sửa:
  **7/7 đạt, Python 3.14.7**. Không cần boto3/credentials/Terraform init; không
  chạy HTTP/AWS thật, integration scripts hoặc Terraform apply.
- [Kết quả test từ clone mới](../evidence/session14-2026-10-31-mvwetq26/fresh-clone-tests.json).
- Lần clone trong sandbox bị từ chối ghi Git HEAD; clone lại ngoài sandbox vào
  thư mục mới thành công. Không coi lỗi môi trường này là lỗi ứng dụng.

## Diff dự kiến

- README/project-summary: trạng thái cleanup 14 tài nguyên ngày 31/10/2026,
  phân biệt dữ liệu lịch sử với dịch vụ live; test offline dễ tìm, runtime là
  cấu hình, profile là điều kiện khi triển khai. Bỏ hướng dẫn hiểu nhầm rằng
  dashboard đã xóa vẫn xem được hoặc plan sau cleanup phải không thay đổi.
- Thêm nhật ký session13 và toàn bộ JSON evidence session13 đã lọc để các link
  trong nhật ký hoạt động, bao gồm kết quả trung gian và verified cuối.
- Thêm nhật ký này và JSON kết quả test; không thêm ảnh mới, code, dependency,
  CI hoặc license. Giữ nguyên source Python/tests/Terraform và evidence cũ.
- SHARE-NOTES bản clone phân biệt snapshot chặng11 với hiện trạng, dẫn người
  đọc tới README và kết quả cleanup. Manifest/checksum chặng11 giữ byte gốc.
- PORTFOLIO-MANIFEST/SHA256SUMS mới trong candidate kiểm tra toàn bộ file hiện
  có trừ chính hai file này để tránh tự tham chiếu. Hash của các file evidence
  lịch sử không bị ghi đè. Đây là checksum local, không phải chữ ký bảo mật.

Chỉ bổ sung tài liệu/evidence công khai đã rà soát. Không copy output, state,
backup, saved plan, private tfvars, raw apply log, credentials hoặc dữ liệu
trình duyệt. Account ID/ARN và profile/resource names tiếp tục được giữ như
metadata; không dùng chúng như credentials hoặc che việc sửa minh chứng.

## Kết quả cleanup được trích dẫn

Session13 xác nhận 14 destroyed, state không còn managed resource. Có 13 kiểm
tra trực tiếp và 1 qua parent absence (SNS policy theo topic). Dashboard ban
đầu chưa được bộ kiểm tra nhận diện mã ResourceNotFound, đã xác minh lại.
Đây là kết quả session13; **chặng14 không gọi AWS để kiểm tra lại**.

Metrics lịch sử có thể còn theo retention. Chưa xác minh billing cuối cùng,
chi phí toàn account bằng 0, deployment từ clone mới hoặc hoạt động dài hạn.
Tái triển khai sau cleanup là thao tác riêng cần được cho phép, không phải
bước kiểm tra offline. Không thêm license hoặc khẳng định miễn phí/credit.

## Điểm dừng

Commit message đề xuất: `Document WS04 cleanup and verify offline tests from a fresh clone`.
Danh sách file/diff/kết quả kiểm tra được lưu dưới
`output/github/session14-2026-10-31-mvwetq26/` (Git-ignored), không tự xuất bản.
Checkout nằm ngoài workspace; vị trí riêng tư ghi ở location.json của thư mục đó.
Chưa commit, push, tạo PR hoặc kiểm chứng phiên bản mới trên GitHub UI.
Chỉ sau khi người dùng duyệt diff mới thực hiện publication; nếu HEAD remote
thay đổi cần đối chiếu lại, không force-push.
