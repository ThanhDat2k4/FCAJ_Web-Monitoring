"""Local mock tests. No HTTP requests, AWS calls, or evidence files are used."""

import io
import json
import os
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from src import app


class WebsiteCheckTests(unittest.TestCase):
    def setUp(self):
        self.target_url = "https://example.com"
        self.context = SimpleNamespace(aws_request_id="local-mock-request-id")
        self.enterContext(patch.dict(os.environ, {
            "TARGET_URL": self.target_url,
            "HTTP_TIMEOUT_SECONDS": "2.5",
        }))
        # Patch where lambda_handler looks up urlopen, preventing real HTTP.
        self.urlopen = self.enterContext(patch.object(app, "urlopen"))
        self.cloudwatch = MagicMock()
        self.client_factory = self.enterContext(patch.object(
            app, "_get_cloudwatch_client", return_value=self.cloudwatch
        ))
        self.print_log = self.enterContext(patch("builtins.print"))

    def assert_result(self, result, *, healthy, status, error):
        self.assertIs(result["is_healthy"], healthy)
        self.assertEqual(result["http_status"], status)
        self.assertEqual(result["error"], error)
        self.assertEqual(result["request_id"], self.context.aws_request_id)
        self.assertEqual(result["target_url"], self.target_url)
        self.print_log.assert_called_once()
        logged = json.loads(self.print_log.call_args.args[0])
        self.assertEqual(logged, result)
        self.urlopen.assert_called_once()
        request = self.urlopen.call_args.args[0]
        self.assertEqual(request.full_url, self.target_url)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(self.urlopen.call_args.kwargs, {"timeout": 2.5})
        self.assert_metrics(result)

    def assert_metrics(self, result):
        self.client_factory.assert_called_once_with()
        self.cloudwatch.put_metric_data.assert_called_once_with(
            Namespace="FCAJ/WebsiteMonitoring",
            MetricData=[{
                "MetricName": name,
                "Dimensions": [{"Name": "MonitorId", "Value": "ws04-main"}],
                "Timestamp": datetime.fromisoformat(result["timestamp"]),
                "Value": value,
                "Unit": unit,
                "StorageResolution": 60,
            } for name, value, unit in (
                ("Availability", 1 if result["is_healthy"] else 0, "None"),
                ("Latency", result["latency_ms"], "Milliseconds"),
            )],
        )

    def test_http_200_is_healthy(self):
        response = MagicMock()
        response.status = 200
        self.urlopen.return_value.__enter__.return_value = response

        # Event input must not override the configured URL.
        result = app.lambda_handler({"target_url": "https://ignored.invalid"}, self.context)

        self.assert_result(result, healthy=True, status=200, error=None)
        self.urlopen.return_value.__exit__.assert_called_once()

    def test_http_503_is_unhealthy(self):
        body = io.BytesIO(b"Service unavailable")
        self.addCleanup(body.close)
        # urllib raises HTTPError for 503 rather than returning a response.
        self.urlopen.side_effect = HTTPError(
            self.target_url, 503, "Service Unavailable", {}, body
        )

        result = app.lambda_handler({}, self.context)

        self.assert_result(result, healthy=False, status=503, error="HTTP 503")
        self.assertTrue(body.closed)

    def test_connection_error_is_unhealthy(self):
        self.urlopen.side_effect = URLError("connection refused")

        result = app.lambda_handler({}, self.context)

        self.assert_result(
            result, healthy=False, status=None,
            error="<urlopen error connection refused>",
        )

    def test_direct_timeout_is_unhealthy(self):
        self.urlopen.side_effect = TimeoutError("timed out")

        result = app.lambda_handler({}, self.context)

        self.assert_result(result, healthy=False, status=None, error="timed out")

    def test_wrapped_timeout_is_unhealthy(self):
        self.urlopen.side_effect = URLError(TimeoutError("timed out"))

        result = app.lambda_handler({}, self.context)

        self.assert_result(
            result, healthy=False, status=None, error="<urlopen error timed out>"
        )

    def test_metric_failure_propagates_and_preserves_healthy_log(self):
        response = MagicMock()
        response.status = 200
        self.urlopen.return_value.__enter__.return_value = response
        failure = OSError("CloudWatch connection failed")
        self.cloudwatch.put_metric_data.side_effect = failure

        with self.assertRaises(OSError) as raised:
            app.lambda_handler({}, self.context)

        self.assertIs(raised.exception, failure)
        self.assertEqual(self.print_log.call_count, 2)
        website, metric_error = [json.loads(call.args[0])
                                 for call in self.print_log.call_args_list]
        self.assertEqual(website["event"], "website_check")
        self.assertIs(website["is_healthy"], True)
        self.assertEqual(website["http_status"], 200)
        self.assertIsNone(website["error"])
        self.assertEqual(metric_error, {
            "event": "metrics_publish_error",
            "request_id": self.context.aws_request_id,
            "namespace": "FCAJ/WebsiteMonitoring",
            "monitor_id": "ws04-main",
            "error_type": "OSError",
            "error": "CloudWatch connection failed",
        })
        self.assertEqual(website["request_id"], self.context.aws_request_id)
        self.assert_metrics(website)

    def test_metric_failure_propagates_and_preserves_http_503_log(self):
        self.urlopen.side_effect = HTTPError(
            self.target_url, 503, "Service Unavailable", {}, None
        )
        failure = RuntimeError("PutMetricData denied")
        self.cloudwatch.put_metric_data.side_effect = failure

        with self.assertRaises(RuntimeError) as raised:
            app.lambda_handler({}, self.context)

        self.assertIs(raised.exception, failure)
        self.assertEqual(self.print_log.call_count, 2)
        website, metric_error = [json.loads(call.args[0])
                                 for call in self.print_log.call_args_list]
        self.assertEqual(website["http_status"], 503)
        self.assertIs(website["is_healthy"], False)
        self.assertEqual(website["error"], "HTTP 503")
        self.assertEqual(metric_error["event"], "metrics_publish_error")
        self.assertEqual(metric_error["error"], "PutMetricData denied")
        self.assertEqual(metric_error["request_id"], self.context.aws_request_id)
        self.assert_metrics(website)


if __name__ == "__main__":
    unittest.main()
