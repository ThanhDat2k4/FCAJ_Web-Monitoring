variable "alert_email" {
  description = "SNS recipient. Set only in a gitignored local auto.tfvars.json file."
  type        = string
  sensitive   = true
  nullable    = false

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "Provide a valid email address without whitespace."
  }
}

data "aws_partition" "current" {}

locals {
  availability_alarm_name = "${local.function_name}-availability-demo"
  # Compute the exact ARN without referencing the alarm resource: no policy cycle.
  availability_alarm_arn = "arn:${data.aws_partition.current.partition}:cloudwatch:${local.dashboard_region}:${data.aws_caller_identity.current.account_id}:alarm:${local.availability_alarm_name}"
}

resource "aws_sns_topic" "monitoring_alerts" {
  name       = "${local.function_name}-alerts"
  fifo_topic = false
}

resource "aws_sns_topic_policy" "monitoring_alerts" {
  arn = aws_sns_topic.monitoring_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "OwnerTopicAdministration"
        Effect = "Allow"
        Principal = {
          AWS = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = [
          "sns:GetTopicAttributes", "sns:SetTopicAttributes", "sns:AddPermission",
          "sns:RemovePermission", "sns:DeleteTopic", "sns:Subscribe",
          "sns:ListSubscriptionsByTopic"
        ]
        Resource = aws_sns_topic.monitoring_alerts.arn
      },
      {
        Sid       = "PublishOnlyFromAvailabilityAlarm"
        Effect    = "Allow"
        Principal = { Service = "cloudwatch.amazonaws.com" }
        Action    = "sns:Publish"
        Resource  = aws_sns_topic.monitoring_alerts.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
            "aws:SourceArn"     = local.availability_alarm_arn
          }
        }
      }
    ]
  })
}

resource "aws_sns_topic_subscription" "monitoring_email" {
  topic_arn              = aws_sns_topic.monitoring_alerts.arn
  protocol               = "email"
  endpoint               = var.alert_email
  endpoint_auto_confirms = false

  depends_on = [aws_sns_topic_policy.monitoring_alerts]
}

resource "aws_cloudwatch_metric_alarm" "availability" {
  alarm_name          = local.availability_alarm_name
  alarm_description   = "WS04 demo: unhealthy check. Missing data is unknown; this does not detect a stopped monitor."
  namespace           = local.metrics_namespace
  metric_name         = "Availability"
  dimensions          = { MonitorId = local.monitor_id }
  statistic           = "Minimum"
  unit                = "None"
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  period              = 60
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "missing"
  actions_enabled     = true

  alarm_actions             = [aws_sns_topic.monitoring_alerts.arn]
  ok_actions                = [aws_sns_topic.monitoring_alerts.arn]
  insufficient_data_actions = []

  depends_on = [aws_sns_topic_policy.monitoring_alerts]
}

output "monitoring_alarm_name" {
  value = aws_cloudwatch_metric_alarm.availability.alarm_name
}

output "monitoring_alert_topic_arn" {
  value = aws_sns_topic.monitoring_alerts.arn
}
