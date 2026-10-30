variable "target_url" {
  description = "Website URL to monitor. Do not include secrets."
  type        = string
  default     = "https://example.com"

  validation {
    condition     = can(regex("^https?://", var.target_url))
    error_message = "target_url must start with http:// or https://."
  }
}

data "archive_file" "monitoring_lambda" {
  type        = "zip"
  source_file = "${path.module}/../src/app.py"
  output_path = "${path.module}/monitoring-lambda.zip"
}

resource "aws_lambda_function" "monitoring" {
  function_name = local.function_name
  description   = "Check website availability and log the result."

  role    = aws_iam_role.monitoring_lambda.arn
  handler = "app.lambda_handler"
  runtime = "python3.13"

  filename         = data.archive_file.monitoring_lambda.output_path
  source_code_hash = data.archive_file.monitoring_lambda.output_base64sha256

  timeout     = 15
  memory_size = 128

  environment {
    variables = {
      TARGET_URL           = var.target_url
      HTTP_TIMEOUT_SECONDS = "5"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.monitoring,
    aws_iam_role_policy.monitoring_logs,
    aws_iam_role_policy.monitoring_metrics
  ]
}

output "monitoring_lambda_name" {
  description = "Name of the website monitoring Lambda."
  value       = aws_lambda_function.monitoring.function_name
}
