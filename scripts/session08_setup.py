"""Create only the reviewed alarm/SNS resources; never start the E2E test.

Email is read from a gitignored local file. Evidence redacts the endpoint;
confirmation/unsubscribe URLs and Terraform state are never requested.
"""

import argparse
import json
import re

from session05_failure_recovery import ROOT, INFRA, aws, run, save


ACCOUNT = "244477277232"
REGION = "ap-southeast-1"
FUNCTION = "fcaj-ws04-Web_monitoring"
ALARM = f"{FUNCTION}-availability-demo"
TOPIC = f"arn:aws:sns:{REGION}:{ACCOUNT}:{FUNCTION}-alerts"


def schedule():
    return aws("scheduler", "get-schedule", "--name", f"{FUNCTION}-every-5-minutes",
               "--group-name", FUNCTION)


def configuration():
    return aws("lambda", "get-function-configuration", "--function-name", FUNCTION)


def inspect_plan(path):
    plan = json.loads(run(["terraform", "show", "-json", str(path)], cwd=INFRA))
    changes = {item["address"]: item["change"] for item in plan["resource_changes"]
               if item["change"]["actions"] != ["no-op"]}
    managed = {key: val for key, val in changes.items() if not key.startswith("data.")}
    expected = {"aws_sns_topic.monitoring_alerts", "aws_sns_topic_policy.monitoring_alerts",
                "aws_sns_topic_subscription.monitoring_email", "aws_cloudwatch_metric_alarm.availability"}
    if set(managed) != expected or any(v["actions"] != ["create"] for v in managed.values()):
        raise RuntimeError("Plan must only create the four authorized alarm/SNS resources")
    if any(v["actions"] != ["read"] for key, v in changes.items() if key.startswith("data.")):
        raise RuntimeError("Unexpected data-source action")
    alarm = managed["aws_cloudwatch_metric_alarm.availability"]["after"]
    required = {"alarm_name": ALARM, "namespace": "FCAJ/WebsiteMonitoring",
                "metric_name": "Availability", "dimensions": {"MonitorId": "ws04-main"},
                "statistic": "Minimum", "unit": "None", "comparison_operator": "LessThanThreshold",
                "threshold": 1, "period": 60, "evaluation_periods": 1,
                "datapoints_to_alarm": 1, "treat_missing_data": "missing",
                "actions_enabled": True}
    if (any(alarm.get(k) != v for k, v in required.items())
            or alarm.get("insufficient_data_actions") not in (None, [])):
        raise RuntimeError("Alarm plan differs from demo specification")
    subscription = managed["aws_sns_topic_subscription.monitoring_email"]
    if (subscription["after"]["protocol"] != "email"
            or not subscription.get("after_sensitive", {}).get("endpoint")):
        raise RuntimeError("Subscription endpoint must be sensitive and use email")
    if managed["aws_sns_topic.monitoring_alerts"]["after"]["fifo_topic"]:
        raise RuntimeError("Topic must be Standard")
    output_changes = {key for key, val in plan.get("output_changes", {}).items()
                      if val["actions"] != ["no-op"]}
    if output_changes != {"monitoring_alarm_name", "monitoring_alert_topic_arn"}:
        raise RuntimeError("Unexpected output changes")
    return {"changes": [{"address": key, "actions": val["actions"]}
                        for key, val in managed.items()], "endpoint": "[REDACTED]",
            "existing_resources_unchanged": True}


def subscriptions():
    raw = aws("sns", "list-subscriptions-by-topic", "--topic-arn", TOPIC)
    return [{"Protocol": s["Protocol"], "Endpoint": "[REDACTED]",
             "SubscriptionArn": s["SubscriptionArn"],
             "confirmed": s["SubscriptionArn"].startswith("arn:")}
            for s in raw.get("Subscriptions", []) if s["Protocol"] == "email"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    args = parser.parse_args()
    if not re.fullmatch(r"session08-[a-z0-9-]+", args.run_id):
        raise RuntimeError("Invalid run_id")
    directory = ROOT / "evidence" / args.run_id
    directory.mkdir(exist_ok=False)
    email = json.loads((INFRA / "alerts.auto.tfvars.json").read_text(encoding="utf-8"))["alert_email"]
    report = {"account": ACCOUNT, "region": REGION, "errors": [],
              "e2e_started": False, "email_receipt_confirmed_by_user": False}
    before = None
    before_schedule = None
    try:
        if aws("sts", "get-caller-identity")["Account"] != ACCOUNT:
            raise RuntimeError("Wrong account")
        before_schedule = schedule()
        before = configuration()
        if (before_schedule["State"] != "DISABLED" or before["FunctionArn"] !=
                f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{FUNCTION}"
                or before["Environment"]["Variables"]["TARGET_URL"] != "https://example.com"):
            raise RuntimeError("Scheduler/account/Region/URL preflight mismatch")
        plan_path = INFRA / f"{args.run_id}-create.tfplan"
        save(directory, "create-plan-summary.json", inspect_plan(plan_path))
        print("Applying reviewed plan: 4 create, existing resources unchanged", flush=True)
        run(["terraform", "apply", "-input=false", "-no-color", str(plan_path)], cwd=INFRA)
        alarms = aws("cloudwatch", "describe-alarms", "--alarm-names", ALARM)
        alarm = alarms["MetricAlarms"][0]
        if (alarm["AlarmActions"] != [TOPIC] or alarm["OKActions"] != [TOPIC]
                or alarm["InsufficientDataActions"] != []):
            raise RuntimeError("Alarm SNS actions mismatch")
        save(directory, "alarm-created.json", alarm)
        attrs = aws("sns", "get-topic-attributes", "--topic-arn", TOPIC)["Attributes"]
        policy = json.loads(attrs["Policy"])
        statements = [s for s in policy["Statement"] if s.get("Principal") ==
                      {"Service": "cloudwatch.amazonaws.com"}]
        if (len(statements) != 1 or statements[0]["Action"] != "sns:Publish"
                or statements[0]["Resource"] != TOPIC
                or statements[0]["Condition"] != {"StringEquals": {
                    "aws:SourceAccount": ACCOUNT, "aws:SourceArn": alarm["AlarmArn"]}}):
            raise RuntimeError("SNS publish policy scope mismatch")
        save(directory, "topic-policy.json", policy)
        sub = subscriptions()
        save(directory, "subscription-status-redacted.json", sub)
        report["subscription_confirmed"] = bool(sub) and all(s["confirmed"] for s in sub)
        report["subscription_status"] = "CONFIRMED" if report["subscription_confirmed"] else "PENDING_CONFIRMATION"
        report["awaiting_user_confirmation"] = True
    except Exception as error:
        report["errors"].append(str(error).replace(email, "[REDACTED]"))
    finally:
        try:
            final_schedule = schedule()
            final_config = configuration()
            report["scheduler_disabled"] = final_schedule["State"] == "DISABLED"
            report["scheduler_unchanged"] = final_schedule == before_schedule
            keys = ("CodeSha256", "Role", "Runtime", "Environment", "LoggingConfig", "Timeout", "MemorySize")
            report["lambda_unchanged"] = before is not None and all(before.get(k) == final_config.get(k) for k in keys)
            report["target_url"] = final_config["Environment"]["Variables"]["TARGET_URL"]
            save(directory, "scheduler-final.json", final_schedule)
            final_path = INFRA / f"{args.run_id}-setup-final.tfplan"
            run(["terraform", "plan", "-input=false", "-no-color", f"-out={final_path}"], cwd=INFRA)
            plan = json.loads(run(["terraform", "show", "-json", str(final_path)], cwd=INFRA))
            changes = [{"address": item["address"], "actions": item["change"]["actions"]}
                       for item in plan.get("resource_changes", []) if item["change"]["actions"] != ["no-op"]]
            changed_outputs = [key for key, val in plan.get("output_changes", {}).items()
                               if val["actions"] != ["no-op"]]
            report["final_plan_no_changes"] = not changes and not changed_outputs
            save(directory, "setup-final-plan-summary.json", {"changes": changes,
                 "changed_outputs": changed_outputs, "no_changes": report["final_plan_no_changes"]})
        except Exception as error:
            report["errors"].append(str(error).replace(email, "[REDACTED]"))
        save(directory, "setup-summary.json", report)
        print(json.dumps(report, ensure_ascii=True, indent=2), flush=True)


if __name__ == "__main__":
    main()
