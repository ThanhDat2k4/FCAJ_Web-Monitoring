# Local share bundle

Xem [project summary](docs/project-summary.md), [README](README.md) va [sharing review](docs/session-11-sharing-readiness.md).

Ban nay khong co state, private email tfvars, credentials, auth/browser cache hay .git.
Account ID/ARN/profile/resource names va workspace paths duoc giu lai nhu metadata.
Khong thay account trong Terraform de tao an tuong portable: doc account guard truoc deployment.
README chi doi lenh Set-Location cho thu muc giai nen; .gitignore doc lap them output/.
Source, Terraform va evidence khac giu byte goc. Generated files duoc danh dau trong manifest.

Chi test offline: `python -B -m unittest discover -s tests -v`. Khong can AWS credentials/boto3.
scripts/session05*, session06*, session07*, session08* co the APPLY/INVOKE AWS/GUI EMAIL.
Khong chay hang loat, khong tai su dung plan/hash lich su. Day la source doi chieu thuc nghiem.
scripts/session09_review.py va session11_share_export.py chi local, can source Git workspace;
chung khong phai buoc bat buoc de test bundle. Init providers/deployment khong duoc test o chang nay.
Neu dung Git, khoi tao repository rieng truoc khi dung git check-ignore; bundle khong tu init Git.
Email subscription khi trien khai moi can nguoi dung Confirm; khong sao chep subscription cu.

Doc cac snapshot lich su cung verified-summary; intermediate errors/pending duoc giu nguyen.
Mot anh session03 duoc nhac bang ten trong nhat ky cu khong co trong nguon; khong tai tao.
Chua chon license/chua upload/chua kiem tra GitHub preview. Nguoi dung quyet dinh truoc public.
Metrics/dashboard/alarm/SNS co the phat sinh chi phi; khong bao dam mien phi/credit.
Cleanup rieng, chua chay. Anh da xem bang mat va text scan heuristic khong bao dam tuyet doi.
