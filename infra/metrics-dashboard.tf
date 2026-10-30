locals {
  metrics_namespace = "FCAJ/WebsiteMonitoring"
  monitor_id        = "ws04-main"
  dashboard_region  = "ap-southeast-1"
}

resource "aws_iam_role_policy" "monitoring_metrics" {
  name = "${local.function_name}-publish-metrics"
  role = aws_iam_role.monitoring_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "cloudwatch:PutMetricData"
      Resource = "*"
      Condition = {
        StringEquals = {
          "cloudwatch:namespace" = local.metrics_namespace
        }
      }
    }]
  })
}

resource "aws_cloudwatch_dashboard" "monitoring" {
  dashboard_name = local.function_name

  dashboard_body = jsonencode({
    start          = "-PT3H"
    periodOverride = "inherit"
    widgets = [
      {
        type = "text", x = 0, y = 0, width = 24, height = 2
        properties = {
          markdown = "## WS04 — Website Monitoring\nAvailability: 1 = healthy, 0 = unhealthy. Missing data means no verified check. Latency measures the existing HTTP request interval, not full page load."
        }
      },
      {
        type = "metric", x = 0, y = 2, width = 12, height = 6
        properties = {
          title   = "Availability — Minimum (0 or 1)"
          view    = "timeSeries", region = local.dashboard_region
          period  = 300, stat = "Minimum", stacked = false, liveData = false
          metrics = [[local.metrics_namespace, "Availability", "MonitorId", local.monitor_id]]
          yAxis   = { left = { min = 0, max = 1 } }
        }
      },
      {
        type = "metric", x = 12, y = 2, width = 12, height = 6
        properties = {
          title  = "HTTP request latency — milliseconds"
          view   = "timeSeries", region = local.dashboard_region
          period = 300, stat = "Average", stacked = false, liveData = false
          metrics = [
            [local.metrics_namespace, "Latency", "MonitorId", local.monitor_id, { stat = "Average", label = "Average" }],
            [local.metrics_namespace, "Latency", "MonitorId", local.monitor_id, { stat = "Maximum", label = "Maximum" }]
          ]
          yAxis = { left = { min = 0, label = "ms", showUnits = false } }
        }
      },
      {
        type = "metric", x = 0, y = 8, width = 24, height = 6
        properties = {
          title  = "Lambda invocations and execution errors"
          view   = "timeSeries", region = local.dashboard_region
          period = 300, stat = "Sum", stacked = false, liveData = false
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.monitoring.function_name],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.monitoring.function_name]
          ]
          yAxis = { left = { min = 0 } }
        }
      }
    ]
  })
}

output "monitoring_dashboard_url" {
  description = "Open the website monitoring dashboard in the intended account."
  value       = "https://${local.dashboard_region}.console.aws.amazon.com/cloudwatch/home?region=${local.dashboard_region}#dashboards:name=${aws_cloudwatch_dashboard.monitoring.dashboard_name}"
}
