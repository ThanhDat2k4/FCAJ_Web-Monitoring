"""After human confirmation: real 200 -> 503 -> 200, always restore URL.

No SetAlarmState, direct PutMetricData, SNS publish, or Scheduler updates.
Each phase invokes Lambda once; all waiting afterward uses read APIs only.
"""

import argparse
from datetime import datetime, timezone
import json
import math
import re
import time

from session05_failure_recovery import (
    ROOT, INFRA, aws, run, save, collect_logs, reviewed_plan, wait_for_update,
)
from session08_setup import ACCOUNT, REGION, FUNCTION, ALARM, TOPIC, schedule, configuration


ORIGINAL_URL = "https://example.com"
FAILURE_URL = "https://httpbin.org/status/503"


def now():
    return datetime.now(timezone.utc)


def alarm():
    return aws("cloudwatch", "describe-alarms", "--alarm-names", ALARM)["MetricAlarms"][0]


def history(start):
    return aws("cloudwatch", "describe-alarm-history", "--alarm-name", ALARM,
               "--start-date", start, "--scan-by", "TimestampAscending")


def availability(payload):
    start = datetime.fromisoformat(payload["timestamp"]).replace(second=0, microsecond=0)
    data = aws("cloudwatch", "get-metric-statistics", "--namespace", "FCAJ/WebsiteMonitoring",
               "--metric-name", "Availability", "--dimensions", "Name=MonitorId,Value=ws04-main",
               "--unit", "None", "--period", "60", "--statistics", "Minimum", "Maximum",
               "Average", "SampleCount", "--start-time", start.isoformat(),
               "--end-time", now().isoformat())
    matched = [p for p in data.get("Datapoints", [])
               if datetime.fromisoformat(p["Timestamp"]) == start]
    value = 1 if payload["is_healthy"] else 0
    valid = len(matched) == 1 and matched[0].get("SampleCount") == 1 and all(
        math.isclose(matched[0][stat], value, abs_tol=0.001)
        for stat in ("Minimum", "Maximum", "Average"))
    return {"namespace": "FCAJ/WebsiteMonitoring", "dimension": {"MonitorId": "ws04-main"},
            "period": 60, "start_time": start.isoformat(), "data": data}, valid


def phase(directory, name, expected_http, expected_state, previous_bucket, report):
    # Use the last payload's actual bucket, not a fixed sleep between invocations.
    if previous_bucket is not None:
        while now().replace(second=0, microsecond=0) <= previous_bucket:
            time.sleep(5)
    started = now().isoformat()
    started_ms = int(time.time() * 1000) - 30000
    payload_path = directory / f"{name}-response.json"
    if payload_path.exists():
        raise RuntimeError("Refusing to overwrite response or invoke twice")
    meta = aws("lambda", "invoke", "--function-name", FUNCTION,
               "--invocation-type", "RequestResponse", str(payload_path))
    save(directory, f"{name}-invoke.json", meta)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    result = {"started_at": started, "response": payload,
              "metric_matches": False, "alarm_state_verified": False}
    report["phases"][name] = result
    expected_error = "HTTP 503" if expected_http == 503 else None
    if (meta.get("StatusCode") != 200 or meta.get("FunctionError")
            or payload.get("http_status") != expected_http
            or payload.get("is_healthy") is not (expected_http == 200)
            or payload.get("error") != expected_error):
        raise RuntimeError(f"{name}: actual website/invocation result differs from expected HTTP {expected_http}")
    bucket = datetime.fromisoformat(payload["timestamp"]).replace(second=0, microsecond=0)
    if previous_bucket is not None and bucket <= previous_bucket:
        raise RuntimeError("Two phases landed in the same or an older minute")
    events = collect_logs(payload, started_ms)
    save(directory, f"{name}-log.json", {"log_group": f"/aws/lambda/{FUNCTION}", "events": events})
    result["log_matches"] = any(json.loads(e["message"]) == payload for e in events)
    deadline = time.monotonic() + 600
    current = None
    metrics = None
    while time.monotonic() < deadline:
        metrics, valid = availability(payload)
        current = alarm()
        # ALARM and recovery must be new transitions after this phase's invocation.
        fresh = name == "baseline" or datetime.fromisoformat(current["StateUpdatedTimestamp"]) >= datetime.fromisoformat(started)
        print(f"{name}: HTTP {expected_http}, metric_match={valid}, alarm={current['StateValue']}", flush=True)
        if valid and current["StateValue"] == expected_state and fresh:
            result["metric_matches"] = True
            result["alarm_state_verified"] = True
            break
        time.sleep(min(20, max(0, deadline - time.monotonic())))
    save(directory, f"{name}-metric.json", metrics)
    save(directory, f"{name}-alarm.json", current)
    save(directory, f"{name}-history.json", history(started))
    result["alarm_state"] = current["StateValue"]
    result["state_reason"] = current["StateReason"]
    result["state_updated_at"] = current["StateUpdatedTimestamp"]
    if not result["metric_matches"] or not result["alarm_state_verified"]:
        raise RuntimeError(f"{name}: metric/alarm timeout (10 minutes); do not hold failure URL longer")
    if not result["log_matches"]:
        raise RuntimeError(f"{name}: request_id log not verified")
    return bucket


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--user-confirmed", action="store_true",
                        help="Only supply after the user explicitly confirms subscription")
    args = parser.parse_args()
    if not args.user_confirmed or not re.fullmatch(r"session08-e2e-[a-z0-9-]+", args.run_id):
        raise RuntimeError("Explicit human confirmation and a new run_id are required")
    directory = ROOT / "evidence" / args.run_id
    directory.mkdir(exist_ok=False)
    email = json.loads((INFRA / "alerts.auto.tfvars.json").read_text(encoding="utf-8"))["alert_email"]
    report = {"account": ACCOUNT, "region": REGION, "phases": {}, "errors": [],
              "subscription_confirmed_by_user": True, "alarm_email_received_by_user": None,
              "recovery_email_received_by_user": None}
    initial = None
    initial_schedule = None
    attempted = False
    start = now().isoformat()

    def change_url(name, before_url, after_url):
        path = INFRA / f"{args.run_id}-{name}.tfplan"
        run(["terraform", "plan", "-input=false", "-no-color",
             f"-var=target_url={after_url}", f"-out={path}"], cwd=INFRA)
        summary = reviewed_plan(path, before_url, after_url, allow_noop=True)
        save(directory, f"{name}-plan-summary.json", summary)
        if not summary.get("no_changes"):
            run(["terraform", "apply", "-input=false", "-no-color", str(path)], cwd=INFRA)
        expected_env = dict(initial["Environment"]["Variables"], TARGET_URL=after_url)
        wait_for_update(expected_env, initial)

    try:
        if aws("sts", "get-caller-identity")["Account"] != ACCOUNT:
            raise RuntimeError("Wrong account")
        initial_schedule = schedule()
        initial = configuration()
        if (initial_schedule["State"] != "DISABLED" or initial["FunctionArn"] !=
                f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{FUNCTION}"
                or initial["Environment"]["Variables"]["TARGET_URL"] != ORIGINAL_URL):
            raise RuntimeError("Account/Region/Scheduler/URL preflight mismatch")
        raw = aws("sns", "list-subscriptions-by-topic", "--topic-arn", TOPIC)["Subscriptions"]
        selected = [s for s in raw if s["Protocol"] == "email" and s["Endpoint"] == email]
        if len(selected) != 1 or not selected[0]["SubscriptionArn"].startswith("arn:"):
            raise RuntimeError("The supplied email subscription is not confirmed in AWS")
        save(directory, "subscription-confirmed-redacted.json", {
            "Protocol": "email", "Endpoint": "[REDACTED]", "confirmed": True,
            "SubscriptionArn": selected[0]["SubscriptionArn"]})
        config = alarm()
        if (config["Period"] != 60 or config["TreatMissingData"] != "missing"
                or config["AlarmActions"] != [TOPIC] or config["OKActions"] != [TOPIC]):
            raise RuntimeError("Alarm configuration changed")
        save(directory, "alarm-before.json", config)
        last = phase(directory, "baseline", 200, "OK", None, report)
        attempted = True  # Restore even if apply fails after a partial update.
        change_url("failure", ORIGINAL_URL, FAILURE_URL)
        phase(directory, "failure", 503, "ALARM", last, report)
    except Exception as error:
        report["errors"].append(str(error).replace(email, "[REDACTED]"))
        print(f"Test error: {str(error).replace(email, '[REDACTED]')}", flush=True)
    finally:
        if attempted:
            try:
                print("Restoring original TARGET_URL before waiting for email", flush=True)
                change_url("restore", FAILURE_URL, ORIGINAL_URL)
                report["target_url_restored"] = True
                previous = [datetime.fromisoformat(p["response"]["timestamp"]).replace(second=0, microsecond=0)
                            for p in report["phases"].values() if "timestamp" in p.get("response", {})]
                phase(directory, "recovery", 200, "OK", max(previous) if previous else None, report)
            except Exception as error:
                report["errors"].append(f"Restore/recovery: {str(error).replace(email, '[REDACTED]')}")
        try:
            final_config = configuration()
            final_schedule = schedule()
            report["target_url"] = final_config["Environment"]["Variables"]["TARGET_URL"]
            report["target_url_restored"] = report["target_url"] == ORIGINAL_URL
            report["scheduler_disabled"] = final_schedule["State"] == "DISABLED"
            report["scheduler_unchanged"] = final_schedule == initial_schedule
            report["lambda_code_unchanged"] = initial is not None and final_config["CodeSha256"] == initial["CodeSha256"]
            save(directory, "scheduler-final.json", final_schedule)
            complete_history = history(start)
            save(directory, "alarm-history-all.json", complete_history)
            report["sns_success_actions"] = [
                {"Timestamp": item["Timestamp"], "HistorySummary": item["HistorySummary"]}
                for item in complete_history.get("AlarmHistoryItems", [])
                if item["HistoryItemType"] == "Action" and TOPIC in item["HistorySummary"]
                and "Successfully executed action" in item["HistorySummary"]]
            path = INFRA / f"{args.run_id}-final.tfplan"
            run(["terraform", "plan", "-input=false", "-no-color", f"-out={path}"], cwd=INFRA)
            plan = json.loads(run(["terraform", "show", "-json", str(path)], cwd=INFRA))
            changes = [{"address": item["address"], "actions": item["change"]["actions"]}
                       for item in plan.get("resource_changes", []) if item["change"]["actions"] != ["no-op"]]
            outputs = [k for k, v in plan.get("output_changes", {}).items() if v["actions"] != ["no-op"]]
            report["final_plan_no_changes"] = not changes and not outputs
            save(directory, "final-plan-summary.json", {"changes": changes, "changed_outputs": outputs,
                 "no_changes": report["final_plan_no_changes"]})
        except Exception as error:
            report["errors"].append(f"Final checks: {str(error).replace(email, '[REDACTED]')}")
        save(directory, "summary.json", report)
        print(json.dumps(report, ensure_ascii=True, indent=2), flush=True)


if __name__ == "__main__":
    main()
