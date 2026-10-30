provider "aws" {
  region  = "ap-southeast-1"
  profile = "fcaj-terraform"

  allowed_account_ids = ["244477277232"]

  default_tags {
    tags = {
      Project     = "fcaj-ws04-Web_monitoring"
      Environment = "lab"
      ManagedBy   = "Terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

output "aws_account_id" {
  description = "AWS account used by Terraform."
  value       = data.aws_caller_identity.current.account_id
}

output "aws_identity_arn" {
  description = "AWS identity used by Terraform."
  value       = data.aws_caller_identity.current.arn
}

/* 
  Giải thích:
- Provider: Terraform dùng AWS thông qua profile nào và Region nào.
- allowed_account_ids: hạn chế thao tác nhầm tài khoản.
- Data source: đọc thông tin đang có.
- Output: hiển thị kết quả để kiểm tra.
- Default tags: đặt nhãn mặc định cho các tài nguyên hỗ trợ tag khi tạo sau này.
*/