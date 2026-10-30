"""Deploy the reviewed Scheduler plan, observe briefly, and always disable.

AWS integration experiment. Never invokes Lambda manually. Full Terraform
plan JSON is inspected in memory only; evidence contains selected summaries.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

from session05_failure_recovery import ROOT, INFRA, aws, run, save


ACCOUNT = "244477277232"
REGION = "ap-southeast-1"
FUNCTION = "fcaj-ws04-Web_monitoring"
GROUP = FUNCTION
SCHEDULE = f"{FUNCTION}-every-5-minutes"
ROLE = f"{FUNCTION}-scheduler-role"
POLICY = f"{FUNCTION}-invoke-lambda"
SCHEDULE_ADDRESS = "aws_scheduler_schedule.monitoring"
EXPECTED_CREATES = {
    "aws_scheduler_schedule_group.monitoring",
    SCHEDULE_ADDRESS,
    "aws_iam_role.monitoring_scheduler",
    "aws_iam_role_policy.monitoring_scheduler_invoke",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def schedule():
    return aws("scheduler", "get-schedule", "--name", SCHEDULE,
               "--group-name", GROUP)


def lambda_config():
    config = aws("lambda", "get-function-configuration", "--function-name", FUNCTION)
    keys = ("FunctionArn", "CodeSha256", "Role", "Runtime", "Handler", "Timeout",
            "MemorySize", "Environment", "LoggingConfig")
    # Used for equality in memory; environment values are never printed wholesale.
    return {key: config.get(key) for key in keys}


def inspect_plan(path, mode):
    plan = json.loads(run(["terraform", "show", "-json", str(path)], cwd=INFRA))
    changes = [item for item in plan.get("resource_changes", [])
               if item["change"]["actions"] != ["no-op"]]
    if any(item["actions"] != ["no-op"]
           for item in plan.get("output_changes", {}).values()):
        raise RuntimeError("Unexpected output changes")
    summary = {"mode": mode, "changes": [
        {"address": item["address"], "actions": item["change"]["actions"]}
        for item in changes], "no_changes": not changes}
    if mode == "create":
        if ({item["address"] for item in changes} != EXPECTED_CREATES
                or any(item["change"]["actions"] != ["create"] for item in changes)):
            raise RuntimeError("Create plan must add exactly the four authorized resources")
        scheduled = next(item["change"]["after"] for item in changes
                         if item["address"] == SCHEDULE_ADDRESS)
        if (scheduled["name"] != SCHEDULE or scheduled["group_name"] != GROUP
                or scheduled["state"] != "DISABLED"
                or scheduled["schedule_expression"] != "rate(5 minutes)"
                or scheduled["flexible_time_window"][0]["mode"] != "OFF"
                or scheduled["target"][0]["arn"] !=
                f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{FUNCTION}"
                or json.loads(scheduled["target"][0]["input"]) != {"trigger": "scheduler"}
                or scheduled["target"][0]["retry_policy"] != [{
                    "maximum_event_age_in_seconds": 300, "maximum_retry_attempts": 2}]):
            raise RuntimeError("Unexpected schedule settings in create plan")
    elif mode in ("enable", "disable"):
        if not changes and mode == "disable":
            return summary
        if (len(changes) != 1 or changes[0]["address"] != SCHEDULE_ADDRESS
                or changes[0]["change"]["actions"] != ["update"]):
            raise RuntimeError("Toggle plan must only update the existing schedule")
        change = changes[0]["change"]
        before_state, after_state = (("DISABLED", "ENABLED") if mode == "enable"
                                     else ("ENABLED", "DISABLED"))
        if (change["before"]["state"] != before_state
                or dict(change["before"], state=after_state) != change["after"]):
            raise RuntimeError("Toggle plan changes more than schedule state")
        # Reject computed unknown changes as well as known value differences.
        def unknown(value):
            if isinstance(value, dict):
                return any(unknown(v) for v in value.values())
            if isinstance(value, list):
                return any(unknown(v) for v in value)
            return value is True
        if unknown(change.get("after_unknown", {})):
            raise RuntimeError("Toggle plan has unknown changes")
        summary.update(before_state=before_state, after_state=after_state)
    elif mode == "final":
        if changes:
            raise RuntimeError("Final plan still has changes")
    else:
        raise RuntimeError("Unknown plan mode")
    return summary


def make_plan(path, enabled):
    run(["terraform", "plan", "-input=false", "-no-color",
         f"-var=scheduler_enabled={str(enabled).lower()}", f"-out={path}"], cwd=INFRA)


def apply(path):
    print(f"Applying checked plan: {path.name}", flush=True)
    run(["terraform", "apply", "-input=false", "-no-color", str(path)], cwd=INFRA)


def check_schedule(config, state):
    if (config["State"] != state or config["GroupName"] != GROUP
            or config["ScheduleExpression"] != "rate(5 minutes)"
            or config["FlexibleTimeWindow"] != {"Mode": "OFF"}
            or config["Target"]["Arn"] !=
            f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{FUNCTION}"
            or config["Target"]["RoleArn"] != f"arn:aws:iam::{ACCOUNT}:role/{ROLE}"
            or json.loads(config["Target"]["Input"]) != {"trigger": "scheduler"}
            or config["Target"]["RetryPolicy"] != {
                "MaximumEventAgeInSeconds": 300, "MaximumRetryAttempts": 2}):
        raise RuntimeError(f"AWS schedule does not match expected {state} settings")


def verify_iam(directory):
    group = aws("scheduler", "get-schedule-group", "--name", GROUP)
    role = aws("iam", "get-role", "--role-name", ROLE, "--query",
               "Role.{Arn:Arn,RoleName:RoleName,Trust:AssumeRolePolicyDocument}")
    policy = aws("iam", "get-role-policy", "--role-name", ROLE,
                 "--policy-name", POLICY)
    expected_trust = {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Principal": {"Service": "scheduler.amazonaws.com"},
        "Action": "sts:AssumeRole", "Condition": {"StringEquals": {
            "aws:SourceAccount": ACCOUNT, "aws:SourceArn": group["Arn"]}}}]}
    expected_policy = {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Action": "lambda:InvokeFunction",
        "Resource": f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{FUNCTION}"}]}
    if role["Trust"] != expected_trust or policy["PolicyDocument"] != expected_policy:
        raise RuntimeError("AWS Scheduler IAM trust/invoke policy differs from expected")
    save(directory, "schedule-group.json", group)
    save(directory, "scheduler-role.json", role)
    save(directory, "scheduler-policy.json", policy)


def read_checks(start_ms, end_ms):
    events = []
    pagination = []
    for _ in range(10):
        page = aws("logs", "filter-log-events", "--log-group-name",
                   f"/aws/lambda/{FUNCTION}", "--start-time", str(start_ms),
                   "--end-time", str(end_ms), "--filter-pattern",
                   '{ $.event = "website_check" }', "--limit", "100",
                   "--no-paginate", *pagination)
        for event in page.get("events", []):
            message = json.loads(event["message"])
            if (message.get("event") == "website_check"
                    and all(key in message for key in
                            ("timestamp", "request_id", "http_status", "is_healthy"))):
                events.append(event)
        token = page.get("nextToken")
        if not token or pagination == ["--next-token", token]:
            break
        pagination = ["--next-token", token]
    return events


def metrics(start, end):
    readings = {}
    for namespace, metric, dimension, value in (
        ("AWS/Scheduler", "InvocationAttemptCount", "ScheduleGroup", GROUP),
        ("AWS/Scheduler", "TargetErrorCount", "ScheduleGroup", GROUP),
        ("AWS/Lambda", "Invocations", "FunctionName", FUNCTION),
        ("AWS/Lambda", "Errors", "FunctionName", FUNCTION),
    ):
        readings[f"{namespace}/{metric}"] = aws(
            "cloudwatch", "get-metric-statistics", "--namespace", namespace,
            "--metric-name", metric, "--dimensions", f"Name={dimension},Value={value}",
            "--start-time", start, "--end-time", end,
            "--period", "60", "--statistics", "Sum")
    return readings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    args = parser.parse_args()
    if not re.fullmatch(r"session06-[a-z0-9-]+", args.run_id):
        raise RuntimeError("Invalid run_id")
    directory = ROOT / "evidence" / args.run_id
    directory.mkdir(exist_ok=False)
    report = {"account": ACCOUNT, "region": REGION, "function": FUNCTION,
              "group": GROUP, "schedule": SCHEDULE, "errors": [],
              "manual_invocations": 0, "observed_runs": [], "disabled": False}
    enabled_attempted = False
    created = False
    initial = None
    observed = {}
    start_ms = None
    try:
        identity = aws("sts", "get-caller-identity")
        if identity["Account"] != ACCOUNT:
            raise RuntimeError("Wrong AWS account")
        initial = lambda_config()
        if (initial["FunctionArn"] !=
                f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{FUNCTION}"
                or initial["Environment"]["Variables"]["TARGET_URL"] != "https://example.com"):
            raise RuntimeError("Lambda preflight mismatch")
        creation = INFRA / f"{args.run_id}-create.tfplan"
        save(directory, "create-plan-summary.json", inspect_plan(creation, "create"))
        apply(creation)
        created = True
        disabled_config = schedule()
        check_schedule(disabled_config, "DISABLED")
        report["disabled"] = True
        save(directory, "schedule-initial-disabled.json", disabled_config)
        verify_iam(directory)
        print("Created and verified four resources; schedule DISABLED", flush=True)

        enable = INFRA / f"{args.run_id}-enable.tfplan"
        make_plan(enable, True)
        save(directory, "enable-plan-summary.json", inspect_plan(enable, "enable"))
        report["enable_requested_at"] = now()
        start_ms = int(time.time() * 1000)
        enabled_attempted = True
        report["disabled"] = False
        apply(enable)
        enabled_config = schedule()
        check_schedule(enabled_config, "ENABLED")
        report["enabled_confirmed_at"] = now()
        save(directory, "schedule-enabled.json", enabled_config)
        # Persist the activation times before waiting, without overwriting evidence.
        save(directory, "activation.json", {
            key: report[key] for key in ("enable_requested_at", "enabled_confirmed_at")})
        print(f"Schedule ENABLED at {report['enabled_confirmed_at']}", flush=True)

        # The deadline includes time taken by the enable apply, never 15 minutes plus apply.
        deadline = time.monotonic() + max(0, 900 - (time.time() - start_ms / 1000))
        while time.monotonic() < deadline:
            for event in read_checks(start_ms, int(time.time() * 1000)):
                payload = json.loads(event["message"])
                observed[payload["request_id"]] = event
            print(f"Observation at {now()}: {len(observed)} distinct website_check request_ids",
                  flush=True)
            if len(observed) >= 2:
                break
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(30, remaining))
        report["observation_ended_at"] = now()
        report["observed_runs"] = [json.loads(event["message"])
                                   for event in observed.values()]
        report["attribution"] = (
            "Logs directly prove executions and HTTP results. Scheduler attribution "
            "is inferred from enabled configuration, timing, metrics if present, "
            "and no manual invocations by this experiment; app does not log trigger."
        )
    except Exception as error:
        report["errors"].append(str(error))
        print(f"Experiment error: {error}", flush=True)
    finally:
        if enabled_attempted:
            try:
                print("Disabling schedule via Terraform", flush=True)
                disable = INFRA / f"{args.run_id}-disable.tfplan"
                make_plan(disable, False)
                summary = inspect_plan(disable, "disable")
                save(directory, "disable-plan-summary.json", summary)
                report["disable_requested_at"] = now()
                if not summary["no_changes"]:
                    apply(disable)
                config = schedule()
                check_schedule(config, "DISABLED")
                report["disabled"] = True
                report["disabled_confirmed_at"] = now()
                save(directory, "schedule-final-disabled.json", config)
                print(f"AWS confirms DISABLED at {report['disabled_confirmed_at']}", flush=True)
            except Exception as error:
                report["errors"].append(f"Disable: {error}")
                print(f"Disable error: {error}", flush=True)
        if created:
            try:
                final = INFRA / f"{args.run_id}-final.tfplan"
                make_plan(final, False)
                summary = inspect_plan(final, "final")
                save(directory, "final-plan-summary.json", summary)
                report["final_plan_no_changes"] = summary["no_changes"]
                report["lambda_configuration_unchanged"] = lambda_config() == initial
                if not report["lambda_configuration_unchanged"]:
                    report["errors"].append("Lambda configuration changed during observation")
            except Exception as error:
                report["errors"].append(f"Final verification: {error}")
        if report.get("enable_requested_at"):
            try:
                save(directory, "metrics.json", metrics(report["enable_requested_at"], now()))
            except Exception as error:
                report["errors"].append(f"Metrics read: {error}")
        if start_ms is not None:
            report["observed_runs"] = [json.loads(event["message"])
                                       for event in observed.values()]
            save(directory, "observed-logs.json", {
                "log_group": f"/aws/lambda/{FUNCTION}",
                "start_time_ms": start_ms, "events": list(observed.values())})
        save(directory, "summary.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
