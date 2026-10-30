import json
import os
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


METRICS_NAMESPACE = "FCAJ/WebsiteMonitoring"
MONITOR_ID = "ws04-main"


def _get_cloudwatch_client():
    # Lambda includes boto3/botocore. Lazy imports keep local mock tests offline.
    import boto3
    from botocore.config import Config

    return boto3.client(
        "cloudwatch",
        config=Config(connect_timeout=2, read_timeout=2,
                      retries={"total_max_attempts": 1}),
    )


def _publish_metrics(result):
    timestamp = datetime.fromisoformat(result["timestamp"])
    metric_data = [
        {
            "MetricName": name,
            "Dimensions": [{"Name": "MonitorId", "Value": MONITOR_ID}],
            "Timestamp": timestamp,
            "Value": value,
            "Unit": unit,
            "StorageResolution": 60,
        }
        for name, value, unit in (
            ("Availability", 1 if result["is_healthy"] else 0, "None"),
            ("Latency", result["latency_ms"], "Milliseconds"),
        )
    ]
    _get_cloudwatch_client().put_metric_data(
        Namespace=METRICS_NAMESPACE, MetricData=metric_data
    )


def lambda_handler(event, context):
    # URL được cấu hình bởi người triển khai.
    # Không nhận URL tùy ý từ dữ liệu event.
    target_url = os.environ["TARGET_URL"]
    timeout_seconds = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "5"))

    started = time.perf_counter()
    http_status = None
    error_message = None

    try:
        request = Request(
            target_url,
            headers={"User-Agent": "FCAJ-Website-Monitor/1.0"},
            method="GET",
        )

        with urlopen(request, timeout=timeout_seconds) as response:
            http_status = response.status

    except HTTPError as error:
        # Website trả lỗi HTTP, ví dụ 404 hoặc 503.
        http_status = error.code
        error_message = f"HTTP {error.code}"
        error.close()

    except (URLError, TimeoutError, OSError) as error:
        # Ví dụ: DNS lỗi, không kết nối được hoặc timeout.
        error_message = str(error)[:500]

    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    is_healthy = (
        http_status is not None
        and 200 <= http_status < 300
    )

    result = {
        "event": "website_check",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": context.aws_request_id,
        "target_url": target_url,
        "http_status": http_status,
        "latency_ms": latency_ms,
        "is_healthy": is_healthy,
        "error": error_message,
    }

    # Ghi cùng kết quả vào CloudWatch Logs.
    print(json.dumps(result, ensure_ascii=False))

    # Publish outside the HTTP exception handlers: a monitoring failure must fail
    # the invocation, while preserving the website result already logged above.
    try:
        _publish_metrics(result)
    except Exception as error:
        print(json.dumps({
            "event": "metrics_publish_error",
            "request_id": context.aws_request_id,
            "namespace": METRICS_NAMESPACE,
            "monitor_id": MONITOR_ID,
            "error_type": type(error).__name__,
            "error": str(error)[:500],
        }, ensure_ascii=False))
        raise

    return result
