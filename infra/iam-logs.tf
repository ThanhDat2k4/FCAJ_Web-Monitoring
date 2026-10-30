locals {
  function_name = "fcaj-ws04-Web_monitoring"
}

resource "aws_cloudwatch_log_group" "monitoring" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 1
}

resource "aws_iam_role" "monitoring_lambda" {
  name = "${local.function_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "AllowLambdaToAssumeRole"
        Effect = "Allow"

        Principal = {
          Service = "lambda.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "monitoring_logs" {
  name = "${local.function_name}-write-logs"
  role = aws_iam_role.monitoring_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "WriteMonitoringLogs"
        Effect = "Allow"

        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]

        Resource = "${aws_cloudwatch_log_group.monitoring.arn}:*"
      }
    ]
  })
}

output "monitoring_lambda_role_arn" {
  description = "Execution role ARN for the monitoring Lambda."
  value       = aws_iam_role.monitoring_lambda.arn
}

output "monitoring_log_group_name" {
  description = "CloudWatch log group for the monitoring Lambda."
  value       = aws_cloudwatch_log_group.monitoring.name
}