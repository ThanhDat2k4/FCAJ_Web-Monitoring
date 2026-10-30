"""Local documentation/privacy review. No network or AWS commands.

Reads only nonignored project candidates; never opens credentials/state/key
files. Reports paths and finding types, never matching sensitive contents.
"""

import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    p = subprocess.run(["git", *args], cwd=ROOT.parent, capture_output=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--report-name", default="local-review.json")
    args = parser.parse_args()
    if not re.fullmatch(r"session09-[a-z0-9-]+", args.run_id):
        raise RuntimeError("Invalid run_id")
    if not re.fullmatch(r"local-review(?:-final)?\.json", args.report_name):
        raise RuntimeError("Invalid report name")
    destination = ROOT / "evidence" / args.run_id / args.report_name
    if destination.exists():
        raise RuntimeError("Refusing to overwrite a previous review")
    destination.parent.mkdir(exist_ok=True)
    _, listed = git("ls-files", "--cached", "--others", "--exclude-standard", "--", ROOT.name)
    candidates = sorted({ROOT.parent / name for name in listed.splitlines()})
    findings = []
    parsed = 0
    checked = 0
    diagrams = 0
    email_pattern = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
    markers = {
        "aws_access_key_shape": re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
        "private_key_marker": re.compile(r"-----BEGIN (?:[A-Z ]+)?PRIVATE KEY-----"),
        "credential_assignment_shape": re.compile(
            r"(?i)(?:aws_secret_access_key|aws_session_token)\s*[=:]\s*[\"']?[A-Za-z0-9/+]{16,}"),
        "sns_private_link_shape": re.compile(r"https?://[^\s\"<>]*(?:ConfirmSubscription|Unsubscribe|confirmation-v2)[^\s\"<>]*", re.I),
    }
    for path in candidates:
        relative = path.relative_to(ROOT).as_posix()
        name = path.name.lower()
        private_name = (name in {"credentials", "credentials.json", "id_rsa", "id_ed25519"}
                        or name.startswith(".env") or ".tfstate" in name
                        or name.endswith((".tfplan", ".tfvars", ".tfvars.json", ".pem", ".key")))
        if private_name:
            findings.append({"file": relative, "type": "private_file_in_share_candidates_not_read"})
            continue
        if path.suffix.lower() not in {".md", ".py", ".tf", ".json", ".txt", ".hcl"}:
            continue
        raw = path.read_bytes()
        encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            findings.append({"file": relative, "type": "text_encoding_not_reviewed"})
            continue
        checked += 1
        for kind, pattern in markers.items():
            if pattern.search(text):
                findings.append({"file": relative, "type": kind})
        if any(match.group(1).lower() not in {"example.com", "example.org", "example.net", "example.invalid"}
               for match in email_pattern.finditer(text)):
            findings.append({"file": relative, "type": "non_example_email"})
        if path.suffix == ".py":
            ast.parse(text, filename=relative)
            parsed += 1
        if path.suffix == ".md":
            if len(re.findall(r"^```", text, flags=re.M)) % 2:
                findings.append({"file": relative, "type": "unbalanced_code_fences"})
            prose = re.sub(r"```.*?```", "", text, flags=re.S)
            for target in re.findall(r"\]\(([^)]+)\)", prose):
                target = target.strip().strip("<>")
                if re.match(r"^[A-Za-z]+:", target) or target.startswith("#"):
                    continue
                local = unquote(target.split("#", 1)[0])
                target_path = path.parent / local
                if local and not target_path.exists() and target_path.resolve() != destination.resolve():
                    findings.append({"file": relative, "type": "missing_relative_link",
                                     "target": local})
            for diagram in re.findall(r"```mermaid\s*\n(.*?)```", text, flags=re.S):
                diagrams += 1
                lines = [line.strip() for line in diagram.splitlines() if line.strip()]
                node = r"[A-Za-z][A-Za-z0-9_]*(?:\[[^\[\]]+\])?"
                if (not lines or lines[0] != "flowchart LR"
                        or any(not re.fullmatch(node + r"\s*-->\s*" + node, line) for line in lines[1:])):
                    findings.append({"file": relative, "type": "simple_mermaid_static_check_failed"})
    probes = ["infra/terraform.tfstate", "infra/terraform.tfstate.backup", "infra/review.tfplan",
              "infra/.terraform/providers/probe", "infra/alerts.auto.tfvars.json",
              "infra/review.tfvars", ".env", "private.pem", "private.key", "infra/monitoring-lambda.zip"]
    ignores = {}
    for probe in probes:
        code, _ = git("check-ignore", "-q", "--", f"{ROOT.name}/{probe}")
        ignores[probe] = code == 0
        if code != 0:
            findings.append({"file": probe, "type": "ignore_rule_missing"})
    report = {"checked_at": datetime.now(timezone.utc).isoformat(),
              "candidate_text_files_checked": checked, "python_files_parsed": parsed,
              "mermaid_blocks_static_checked": diagrams, "mermaid_rendered": False,
              "relative_markdown_links_checked": True, "external_links_checked": False,
              "binary_images_automatically_scanned": False, "ignored_files_opened": False,
              "ignore_probes": ignores, "findings": findings,
              "scope": "Heuristic review of nonignored WS04 text files, not a secret-free certification"}
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=True, indent=2)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    raise SystemExit(1 if findings else 0)


if __name__ == "__main__":
    main()
