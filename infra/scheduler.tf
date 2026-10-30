variable "scheduler_enabled" {
  description = "Enable periodic website checks. Keep false outside verification."
  type        = bool
  default     = false
}

resource "aws_scheduler_schedule_group" "monitoring" {
  name = local.function_name
}

resource "aws_iam_role" "monitoring_scheduler" {
  name = "${local.function_name}-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "scheduler.amazonaws.com"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          "aws:SourceArn"     = aws_scheduler_schedule_group.monitoring.arn
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "monitoring_scheduler_invoke" {
  name = "${local.function_name}-invoke-lambda"
  role = aws_iam_role.monitoring_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.monitoring.arn
    }]
  })
}

resource "aws_scheduler_schedule" "monitoring" {
  name                         = "${local.function_name}-every-5-minutes"
  group_name                   = aws_scheduler_schedule_group.monitoring.name
  description                  = "Check the WS04 website every five minutes."
  schedule_expression          = "rate(5 minutes)"
  schedule_expression_timezone = "UTC"
  state                        = var.scheduler_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.monitoring.arn
    role_arn = aws_iam_role.monitoring_scheduler.arn
    input    = jsonencode({ trigger = "scheduler" })

    # Delivery retries do not detect an unhealthy website in the Lambda result.
    retry_policy {
      maximum_retry_attempts       = 2
      maximum_event_age_in_seconds = 300
    }
  }

  depends_on = [aws_iam_role_policy.monitoring_scheduler_invoke]
}
