"""Apply the reviewed stage-7 plan and invoke once; only poll reads afterward."""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import time

from session05_failure_recovery import ROOT, INFRA, aws, run, save, collect_logs


ACCOUNT = "244477277232"
REGION = "ap-southeast-1"
FUNCTION = "fcaj-ws04-Web_monitoring"
NAMESPACE = "FCAJ/WebsiteMonitoring"
MONITOR_ID = "ws04-main"
DASHBOARD_URL = (f"https://{REGION}.console.aws.amazon.com/cloudwatch/home"
                 f"?region={REGION}#dashboards:name={FUNCTION}")


def scheduler():
    return aws("scheduler", "get-schedule", "--name", f"{FUNCTION}-every-5-minutes",
               "--group-name", FUNCTION)


def config():
    return aws("lambda", "get-function-configuration", "--function-name", FUNCTION)


def inspect_deploy_plan(path):
    plan = json.loads(run(["terraform", "show", "-json", str(path)], cwd=INFRA))
    changes = {item["address"]: item["change"] for item in plan["resource_changes"]
               if item["change"]["actions"] != ["no-op"]}
    expected = {"aws_cloudwatch_dashboard.monitoring": ["create"],
                "aws_iam_role_policy.monitoring_metrics": ["create"],
                "aws_lambda_function.monitoring": ["update"]}
    if {key: value["actions"] for key, value in changes.items()} != expected:
        raise RuntimeError("Deployment plan includes changes outside scope")
    change = changes["aws_lambda_function.monitoring"]
    before, after = dict(change["before"]), dict(change["after"])
    before_hash, after_hash = before.pop("source_code_hash"), after.pop("source_code_hash")
    before.pop("last_modified", None)
    after.pop("last_modified", None)
    if before != after or before_hash == after_hash:
        raise RuntimeError("Lambda plan must change only code/hash and computed last_modified")
    unknown = dict(change.get("after_unknown", {}))
    unknown.pop("last_modified", None)

    def any_unknown(value):
        if isinstance(value, dict):
            return any(any_unknown(v) for v in value.values())
        if isinstance(value, list):
            return any(any_unknown(v) for v in value)
        return value is True

    if any_unknown(unknown):
        raise RuntimeError("Lambda has unknown planned changes outside last_modified")
    policy_values = changes["aws_iam_role_policy.monitoring_metrics"]["after"]
    expected_policy = {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Action": "cloudwatch:PutMetricData", "Resource": "*",
        "Condition": {"StringEquals": {"cloudwatch:namespace": NAMESPACE}}}]}
    if (policy_values["role"] != f"{FUNCTION}-lambda-role"
            or json.loads(policy_values["policy"]) != expected_policy):
        raise RuntimeError("Metric policy is not limited to the intended role/namespace")
    outputs = {key: val for key, val in plan.get("output_changes", {}).items()
               if val["actions"] != ["no-op"]}
    if (set(outputs) != {"monitoring_dashboard_url"}
            or outputs["monitoring_dashboard_url"]["actions"] != ["create"]
            or outputs["monitoring_dashboard_url"]["after"] != DASHBOARD_URL):
        raise RuntimeError("Unexpected output change")
    body = json.loads(changes["aws_cloudwatch_dashboard.monitoring"]["after"]["dashboard_body"])
    verify_dashboard(body)
    return ({"changes": expected, "before_code_hash": before_hash,
             "after_code_hash": after_hash, "dashboard_url": DASHBOARD_URL}, body)


def verify_dashboard(body):
    widgets = [w["properties"] for w in body["widgets"] if w["type"] == "metric"]
    if len(widgets) != 3 or any(w["region"] != REGION or w["period"] != 300 for w in widgets):
        raise RuntimeError("Dashboard must have three metric widgets in the intended Region")
    availability, latency, native = widgets
    if (availability["stat"] != "Minimum"
            or availability["yAxis"]["left"] != {"min": 0, "max": 1}
            or availability["metrics"] != [[NAMESPACE, "Availability", "MonitorId", MONITOR_ID]]):
        raise RuntimeError("Unexpected Availability widget")
    if (latency["metrics"] != [
        [NAMESPACE, "Latency", "MonitorId", MONITOR_ID,
         {"stat": stat, "label": stat}]
        for stat in ("Average", "Maximum")]):
        raise RuntimeError("Unexpected Latency widget")
    if (native["stat"] != "Sum" or native["metrics"] != [
        ["AWS/Lambda", metric, "FunctionName", FUNCTION] for metric in ("Invocations", "Errors")]):
        raise RuntimeError("Unexpected native Lambda metrics")
    if "FILL(" in json.dumps(body).upper():
        raise RuntimeError("Dashboard must not fabricate missing samples")


def get_metrics(start, end):
    results = {}
    for metric, unit in (("Availability", "None"), ("Latency", "Milliseconds")):
        results[metric] = aws(
            "cloudwatch", "get-metric-statistics", "--namespace", NAMESPACE,
            "--metric-name", metric, "--dimensions", f"Name=MonitorId,Value={MONITOR_ID}",
            "--start-time", start, "--end-time", end, "--period", "60",
            "--unit", unit, "--statistics", "Minimum", "Maximum", "Average", "SampleCount")
    return {"namespace": NAMESPACE, "dimensions": {"MonitorId": MONITOR_ID},
            "start_time": start, "end_time": end, "period": 60,
            "statistics": ["Minimum", "Maximum", "Average", "SampleCount"],
            "results": results}


def metrics_match(reading, payload):
    target_bucket = datetime.fromisoformat(payload["timestamp"]).replace(second=0, microsecond=0)
    for metric, expected in (("Availability", 1 if payload["is_healthy"] else 0),
                              ("Latency", payload["latency_ms"])):
        matches = [p for p in reading["results"][metric].get("Datapoints", [])
                   if datetime.fromisoformat(p["Timestamp"]) == target_bucket]
        if len(matches) != 1 or matches[0].get("SampleCount") != 1:
            return False
        if not all(math.isclose(matches[0][stat], expected, abs_tol=0.001)
                   for stat in ("Minimum", "Maximum", "Average")):
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--verify-deployed", action="store_true",
                        help="Skip apply; verify already deployed code and invoke once if no response exists")
    args = parser.parse_args()
    if not re.fullmatch(r"session07-[a-z0-9-]+", args.run_id):
        raise RuntimeError("Invalid run_id")
    directory = ROOT / "evidence" / args.run_id
    prefix = "verified-" if args.verify_deployed else ""
    if (directory / f"{prefix}summary.json").exists() or (directory / "response.json").exists():
        raise RuntimeError("Refusing to rerun an existing experiment")
    report = {"account": ACCOUNT, "region": REGION, "errors": [],
              "dashboard_url": DASHBOARD_URL, "invocation_commands": 0,
              "console_ui_verified": False}
    initial_scheduler = None
    initial_lambda = None
    try:
        if aws("sts", "get-caller-identity")["Account"] != ACCOUNT:
            raise RuntimeError("Wrong account")
        initial_scheduler = scheduler()
        save(directory, f"{prefix}scheduler-before.json", initial_scheduler)
        if initial_scheduler["State"] != "DISABLED":
            raise RuntimeError("Scheduler must already be DISABLED")
        initial_lambda = config()
        if (initial_lambda["FunctionArn"] !=
                f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{FUNCTION}"
                or initial_lambda["Environment"]["Variables"]["TARGET_URL"] != "https://example.com"):
            raise RuntimeError("Unexpected Lambda account/Region/URL")
        plan_path = INFRA / f"{args.run_id}-deploy-v2.tfplan"
        plan_summary, expected_body = inspect_deploy_plan(plan_path)
        expected_initial_hash = plan_summary["after_code_hash"] if args.verify_deployed else plan_summary["before_code_hash"]
        if initial_lambda["CodeSha256"] != expected_initial_hash:
            raise RuntimeError("Lambda code changed since the reviewed plan")
        save(directory, f"{prefix}deploy-plan-summary.json", plan_summary)
        if not args.verify_deployed:
            print("Applying reviewed plan: 2 create, 1 code update, 0 destroy", flush=True)
            run(["terraform", "apply", "-input=false", "-no-color", str(plan_path)], cwd=INFRA)
        else:
            print("Verifying existing deployment; no apply", flush=True)
        aws("lambda", "wait", "function-updated-v2", "--function-name", FUNCTION)
        deployed = config()
        if deployed["CodeSha256"] != plan_summary["after_code_hash"]:
            raise RuntimeError("Deployed code hash mismatch")
        if scheduler() != initial_scheduler:
            raise RuntimeError("Scheduler configuration changed; refusing invocation")

        dashboard = aws("cloudwatch", "get-dashboard", "--dashboard-name", FUNCTION)
        actual_body = json.loads(dashboard["DashboardBody"])
        verify_dashboard(actual_body)
        if actual_body != expected_body:
            raise RuntimeError("Dashboard API differs from the reviewed plan")
        save(directory, "dashboard-api.json", dashboard)
        report["dashboard_api_verified"] = True
        policy = aws("iam", "get-role-policy", "--role-name", f"{FUNCTION}-lambda-role",
                     "--policy-name", f"{FUNCTION}-publish-metrics")
        save(directory, "metric-policy.json", policy)

        start_ms = int(time.time() * 1000) - 30000
        report["invocation_commands"] = 1
        metadata = aws("lambda", "invoke", "--function-name", FUNCTION,
                       "--invocation-type", "RequestResponse", str(directory / "response.json"))
        save(directory, "invoke.json", metadata)
        payload = json.loads((directory / "response.json").read_text(encoding="utf-8"))
        if metadata.get("FunctionError") or metadata.get("StatusCode") != 200:
            raise RuntimeError("Lambda invocation failed; no second invocation will be attempted")
        report["response"] = payload
        matched = collect_logs(payload, start_ms)
        save(directory, "cloudwatch-log.json", {"log_group": f"/aws/lambda/{FUNCTION}",
                                                "events": matched})
        report["log_matches_response"] = any(json.loads(e["message"]) == payload for e in matched)
        start = datetime.fromisoformat(payload["timestamp"]).replace(second=0, microsecond=0).isoformat()
        deadline = time.monotonic() + 900
        poll_count = 0
        reading = None
        report["metrics_match_response"] = False
        while time.monotonic() < deadline:
            reading = get_metrics(start, datetime.now(timezone.utc).isoformat())
            poll_count += 1
            if metrics_match(reading, payload):
                report["metrics_match_response"] = True
                break
            print(f"Metric read {poll_count}: waiting for matching single-sample datapoints", flush=True)
            time.sleep(min(30, max(0, deadline - time.monotonic())))
        save(directory, "metrics.json", {"poll_count": poll_count, "query": reading})
        print(f"Metric evidence matches response: {report['metrics_match_response']}", flush=True)
    except Exception as error:
        report["errors"].append(str(error))
        print(f"Verification error: {error}", flush=True)
    finally:
        # Read-only final checks; never alter Scheduler in this stage.
        try:
            final_scheduler = scheduler()
            save(directory, f"{prefix}scheduler-final.json", final_scheduler)
            report["scheduler_disabled"] = final_scheduler["State"] == "DISABLED"
            report["scheduler_unchanged"] = final_scheduler == initial_scheduler
            final_config = config()
            invariant_keys = ("FunctionArn", "Role", "Runtime", "Handler", "Timeout",
                              "MemorySize", "Environment", "LoggingConfig")
            report["lambda_configuration_preserved_except_code"] = (
                initial_lambda is not None and all(final_config.get(k) == initial_lambda.get(k)
                                                   for k in invariant_keys))
            final_path = INFRA / f"{args.run_id}-{prefix}final.tfplan"
            run(["terraform", "plan", "-input=false", "-no-color", f"-out={final_path}"], cwd=INFRA)
            final = json.loads(run(["terraform", "show", "-json", str(final_path)], cwd=INFRA))
            changes = [{"address": item["address"], "actions": item["change"]["actions"]}
                       for item in final.get("resource_changes", [])
                       if item["change"]["actions"] != ["no-op"]]
            outputs = [key for key, value in final.get("output_changes", {}).items()
                       if value["actions"] != ["no-op"]]
            report["final_plan_no_changes"] = not changes and not outputs
            save(directory, f"{prefix}final-plan-summary.json", {"changes": changes,
                 "changed_outputs": outputs, "no_changes": report["final_plan_no_changes"]})
        except Exception as error:
            report["errors"].append(f"Final read-only checks: {error}")
        save(directory, f"{prefix}summary.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
