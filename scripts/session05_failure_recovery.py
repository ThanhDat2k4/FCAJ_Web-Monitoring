"""Run the reviewed WS04 experiment; always attempt Terraform restoration.

This is an explicit AWS integration experiment, not part of local mock tests.
Requires an already reviewed <run-id>-failure.tfplan in infra.
"""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"
PROFILE = "fcaj-terraform"
REGION = "ap-southeast-1"
ACCOUNT = "244477277232"
FUNCTION = "fcaj-ws04-Web_monitoring"
ORIGINAL_URL = "https://example.com"
FAILURE_URL = "https://httpbin.org/status/503"
CODE_HASH = "S49/nUz/mocng0C+1WBKHd/nw0tfrILbPKDba+Up6D4="
SOURCE_HASH = "766f9be24bca81191ae7bdebaa13eff6800a387b0bb6fb6dcfcbdd284d6c5bac"


def run(args, cwd=ROOT):
    process_env = dict(os.environ, AWS_MAX_ATTEMPTS="1",
                       AWS_CLI_OUTPUT_ENCODING="UTF-8", AWS_CLI_FILE_ENCODING="UTF-8")
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", env=process_env)
    if result.returncode:
        # Commands here never request credentials, signed URLs or state output.
        raise RuntimeError(f"{args[0]} {args[1]} failed: "
                           + (result.stderr or result.stdout)[-1600:])
    return result.stdout


def aws(*args):
    output = run(["aws", *args, "--profile", PROFILE, "--region", REGION,
                  "--output", "json", "--no-cli-pager"])
    return json.loads(output) if output.strip() else None


def config():
    return aws("lambda", "get-function-configuration", "--function-name", FUNCTION)


def save(directory, name, data):
    with (directory / name).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def reviewed_plan(path, before_url, after_url, allow_noop=False):
    # Full plan JSON is inspected in memory only, never printed or persisted.
    plan = json.loads(run(["terraform", "show", "-json", str(path)], cwd=INFRA))
    changes = [item for item in plan.get("resource_changes", [])
               if item["change"]["actions"] != ["no-op"]]
    for output in plan.get("output_changes", {}).values():
        if output["actions"] != ["no-op"]:
            raise RuntimeError("Plan changes outputs outside this experiment")
    if allow_noop and not changes:
        return {"changes": [], "no_changes": True}
    if len(changes) != 1:
        raise RuntimeError("Plan must change exactly one resource")
    item = changes[0]
    change = item["change"]
    if (item["address"] != "aws_lambda_function.monitoring"
            or change["actions"] != ["update"]):
        raise RuntimeError("Plan is not an in-place update of the expected Lambda")
    before, after = change["before"], change["after"]
    if before["function_name"] != FUNCTION or after["function_name"] != FUNCTION:
        raise RuntimeError("Unexpected function name in plan")
    before_env = before["environment"][0]["variables"]
    after_env = after["environment"][0]["variables"]
    expected_env = dict(before_env, TARGET_URL=after_url)
    if before_env.get("TARGET_URL") != before_url or after_env != expected_env:
        raise RuntimeError("Plan does not preserve all other environment variables")
    # Replacing only TARGET_URL must make the complete planned values identical.
    expected = dict(before, environment=[dict(before["environment"][0],
                                              variables=expected_env)])
    if expected != after:
        raise RuntimeError("Plan changes attributes beyond TARGET_URL")

    def has_unknown(value):
        if isinstance(value, dict):
            return any(has_unknown(v) for v in value.values())
        if isinstance(value, list):
            return any(has_unknown(v) for v in value)
        return value is True

    if has_unknown(change.get("after_unknown", {})):
        raise RuntimeError("Plan has unknown values; cannot prove URL-only change")
    return {"resource": item["address"], "actions": ["update"],
            "only_changed_field": "environment.variables.TARGET_URL",
            "before_url": before_url, "after_url": after_url,
            "add": 0, "change": 1, "destroy": 0}


def make_plan(path, url):
    run(["terraform", "plan", "-input=false", "-no-color",
         f"-var=target_url={url}", f"-out={path}"], cwd=INFRA)


def apply(path):
    print(f"Applying reviewed plan: {path.name}", flush=True)
    run(["terraform", "apply", "-input=false", "-no-color", str(path)], cwd=INFRA)


def wait_for_update(expected_env, initial):
    aws("lambda", "wait", "function-updated-v2", "--function-name", FUNCTION)
    current = config()
    if (current.get("LastUpdateStatus") != "Successful"
            or current.get("State") != "Active"
            or current["Environment"]["Variables"] != expected_env
            or current["CodeSha256"] != initial["CodeSha256"]):
        raise RuntimeError("Post-update verification failed")
    return current


def collect_logs(payload, started_ms):
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not re.fullmatch(r"[a-f0-9-]{36}", request_id):
        raise RuntimeError("Response has no valid request_id")
    matched = []
    # At most four read-only log searches. Lambda itself is invoked only once.
    for attempt in range(4):
        if attempt:
            time.sleep(5)
        page_args = []
        for _ in range(5):
            response = aws(
                "logs", "filter-log-events", "--log-group-name",
                f"/aws/lambda/{FUNCTION}", "--start-time", str(started_ms),
                # UUIDs contain hyphens: CloudWatch requires double quotes.
                "--filter-pattern", json.dumps(request_id), "--no-paginate", *page_args,
            )
            for event in response.get("events", []):
                try:
                    message = json.loads(event["message"])
                except (ValueError, TypeError):
                    continue
                if message.get("request_id") == request_id:
                    matched.append(event)
            token = response.get("nextToken")
            if matched or not token or page_args == ["--next-token", token]:
                break
            page_args = ["--next-token", token]
        if matched:
            break
    return matched


def invoke_and_match(directory, phase, expected_status):
    started_ms = int(time.time() * 1000) - 30000
    payload_file = directory / f"{phase}-response.json"
    if payload_file.exists():
        raise RuntimeError("Refusing to overwrite response evidence")
    metadata = aws("lambda", "invoke", "--function-name", FUNCTION,
                   "--invocation-type", "RequestResponse", str(payload_file))
    save(directory, f"{phase}-invoke.json", metadata)
    payload = json.loads(payload_file.read_text(encoding="utf-8"))
    request_id = payload.get("request_id")
    matched = collect_logs(payload, started_ms)
    save(directory, f"{phase}-cloudwatch.json", {
        "log_group": f"/aws/lambda/{FUNCTION}", "request_id": request_id,
        "events": matched,
    })
    expected_url = FAILURE_URL if expected_status == 503 else ORIGINAL_URL
    expected_error = "HTTP 503" if expected_status == 503 else None
    passed = (
        metadata.get("StatusCode") == 200 and not metadata.get("FunctionError")
        and payload.get("http_status") == expected_status
        and payload.get("is_healthy") is (expected_status == 200)
        and payload.get("error") == expected_error
        and payload.get("target_url") == expected_url
        and any(json.loads(event["message"]) == payload for event in matched)
    )
    summary = {"passed": passed, "request_id": request_id,
               "http_status": payload.get("http_status"),
               "is_healthy": payload.get("is_healthy"), "error": payload.get("error"),
               "matching_log_events": len(matched)}
    print(f"{phase}: {json.dumps(summary)}", flush=True)
    return summary


def verify_existing_logs(directory):
    """Read-only follow-up; preserve the original unsuccessful query evidence."""
    report = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    for phase, status in (("failure", 503), ("recovery", 200)):
        payload = json.loads((directory / f"{phase}-response.json").read_text(encoding="utf-8"))
        metadata = json.loads((directory / f"{phase}-invoke.json").read_text(encoding="utf-8"))
        started_ms = int(datetime.fromisoformat(payload["timestamp"]).timestamp() * 1000) - 30000
        events = collect_logs(payload, started_ms)
        save(directory, f"{phase}-cloudwatch-confirmed.json", {
            "log_group": f"/aws/lambda/{FUNCTION}",
            "request_id": payload["request_id"],
            "filter_pattern": json.dumps(payload["request_id"]),
            "events": events,
        })
        passed = (
            metadata.get("StatusCode") == 200 and not metadata.get("FunctionError")
            and payload.get("http_status") == status
            and payload.get("is_healthy") is (status == 200)
            and payload.get("error") == ("HTTP 503" if status == 503 else None)
            and payload.get("target_url") == (FAILURE_URL if status == 503 else ORIGINAL_URL)
            and any(json.loads(event["message"]) == payload for event in events)
        )
        report[phase]["passed"] = passed
        report[phase]["matching_log_events"] = len(events)
        report[phase]["confirmed_log_file"] = f"{phase}-cloudwatch-confirmed.json"
    report["log_query_correction"] = (
        "Initial UUID terms were unquoted. Requeried the same request_ids using "
        "quoted phrases, with no additional Lambda invocations. Original query "
        "results retained in *-cloudwatch.json and summary.json."
    )
    save(directory, "verified-summary.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--verify-existing-logs", action="store_true",
                        help="Read existing evidence and CloudWatch only; never apply/invoke")
    args = parser.parse_args()
    if not re.fullmatch(r"session05-[a-z0-9-]+", args.run_id):
        raise RuntimeError("Invalid run_id")
    directory = ROOT / "evidence" / args.run_id
    if args.verify_existing_logs:
        verify_existing_logs(directory)
        return
    directory.mkdir(exist_ok=False)
    report = {"account": ACCOUNT, "region": REGION, "function": FUNCTION,
              "original_url": ORIGINAL_URL, "failure_url": FAILURE_URL,
              "errors": [], "restored": False}
    attempted = False
    initial = None
    try:
        identity = aws("sts", "get-caller-identity")
        if identity["Account"] != ACCOUNT:
            raise RuntimeError("Account mismatch")
        initial = config()
        original_env = {"TARGET_URL": ORIGINAL_URL, "HTTP_TIMEOUT_SECONDS": "5"}
        if (initial["FunctionArn"] != f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{FUNCTION}"
                or initial["Environment"]["Variables"] != original_env
                or initial["CodeSha256"] != CODE_HASH
                or hashlib.sha256((ROOT / "src" / "app.py").read_bytes()).hexdigest() != SOURCE_HASH):
            raise RuntimeError("Preflight configuration/code changed; stop")
        report["source_comparison"] = {
            "local_and_deployed_app_sha256": SOURCE_HASH,
            "deployment_package_sha256_base64": CODE_HASH,
            "exact_app_match_verified_before_plan": True,
        }
        failure_plan = INFRA / f"{args.run_id}-failure.tfplan"
        summary = reviewed_plan(failure_plan, ORIGINAL_URL, FAILURE_URL)
        save(directory, "failure-plan-summary.json", summary)
        attempted = True  # Even a partially failed apply must trigger restoration.
        apply(failure_plan)
        wait_for_update(dict(original_env, TARGET_URL=FAILURE_URL), initial)
        report["failure"] = invoke_and_match(directory, "failure", 503)
    except Exception as error:
        report["errors"].append(str(error))
        print(f"Experiment error: {error}", flush=True)
    finally:
        if attempted:
            try:
                print("Restoring original TARGET_URL via Terraform", flush=True)
                restore_plan = INFRA / f"{args.run_id}-restore.tfplan"
                make_plan(restore_plan, ORIGINAL_URL)
                summary = reviewed_plan(restore_plan, FAILURE_URL, ORIGINAL_URL,
                                        allow_noop=True)
                save(directory, "restore-plan-summary.json", summary)
                if not summary.get("no_changes"):
                    apply(restore_plan)
                current = wait_for_update(initial["Environment"]["Variables"], initial)
                report["restored"] = True
                report["restored_configuration"] = {
                    "target_url": current["Environment"]["Variables"]["TARGET_URL"],
                    "all_environment_variables_match_initial": True,
                    "code_hash_matches_initial": True,
                    "last_update_status": current["LastUpdateStatus"],
                }
                report["recovery"] = invoke_and_match(directory, "recovery", 200)
            except Exception as error:
                report["errors"].append(f"Restoration/recovery: {error}")
                print(f"Restoration/recovery error: {error}", flush=True)
            # Check drift even when the recovery invocation or log lookup fails.
            try:
                final_plan = INFRA / f"{args.run_id}-final.tfplan"
                make_plan(final_plan, ORIGINAL_URL)
                summary = reviewed_plan(final_plan, ORIGINAL_URL, ORIGINAL_URL,
                                        allow_noop=True)
                report["final_plan_no_changes"] = summary.get("no_changes", False)
                save(directory, "final-plan-summary.json", summary)
            except Exception as error:
                report["errors"].append(f"Final plan: {error}")
        save(directory, "summary.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
