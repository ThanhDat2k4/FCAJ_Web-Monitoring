"""Local-only allowlist export. Never executes Terraform or integration scripts.

Run only after manually reviewing every image named in REVIEWED_IMAGES.
Uses a new run directory; preserves source evidence and private/ignored files.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
REVIEWED_IMAGES = [
    "2026-10-29_01_aws-identity.png", "2026-10-29_02_terraform-validate.png",
    "2026-10-29_03_terraform-plan.png", "02a_terraform-plan-iam-logs.png",
    "02b_terraform-apply-iam-logs.png", "02c_lambda-role-permissions.png",
    "02d_lambda-role-trust.png", "02e_log-group-retention.png",
    "session09-2026-10-30-mvuocnv1/email-subjects.png",
    "session10-2026-10-30-mvuq082h/dashboard-time-range.png",
    "session10-2026-10-30-mvuq082h/dashboard-widgets.png",
    "session10-2026-10-30-mvuq082h/architecture.png",
    "session10-2026-10-30-mvuq082h/architecture.svg",
]
TEXT = {".md", ".py", ".tf", ".json", ".txt", ".hcl", ".mmd", ".svg"}
MARKERS = {
    "aws_access_key_shape": re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "private_key_marker": re.compile(r"-----BEGIN (?:[A-Z ]+)?PRIVATE KEY-----"),
    "credential_assignment": re.compile(r"(?i)(?:aws_secret_access_key|aws_session_token)\s*[=:]\s*[\"']?[A-Za-z0-9/+]{16,}"),
    "sns_private_url": re.compile(r"https?://[^\s\"<>]*(?:ConfirmSubscription|Unsubscribe|confirmation-v2)[^\s\"<>]*", re.I),
    "signed_url": re.compile(r"[?&](?:X-Amz-Signature|X-Amz-Credential|Signature)=", re.I),
    "user_home_path": re.compile(r"(?i)[A-Z]:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+"),
}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def decode(raw):
    return raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")


def findings(text):
    result = [name for name, pattern in MARKERS.items() if pattern.search(text)]
    if any(m.group(1).lower() not in {"example.com", "example.net", "example.org", "example.invalid"}
           for m in EMAIL.finditer(text)):
        result.append("non_example_email")
    return result


def private_name(path):
    name = path.name.lower()
    return (any(x in path.parts for x in {"output", ".terraform", ".git", "__pycache__", ".venv"})
            or name.startswith(".env") or ".tfstate" in name
            or name.endswith((".tfplan", ".tfvars", ".tfvars.json", ".pem", ".key", ".zip"))
            or name in {"credentials", "credentials.json", "id_rsa", "id_ed25519", "tfplan"})


def image_check(path):
    raw = path.read_bytes()
    if path.suffix == ".svg":
        tree = ET.fromstring(raw)
        assert tree.tag.endswith("svg")
        assert not any(element.tag.rsplit("}", 1)[-1] == "script" for element in tree.iter())
        for element in tree.iter():
            for key, value in element.attrib.items():
                if key.rsplit("}", 1)[-1] in {"href", "src"}:
                    assert not value.lower().startswith(("http:", "https:", "file:", "javascript:"))
        return findings(decode(raw))
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    offset, metadata, ended = 8, [], False
    while offset < len(raw):
        size = struct.unpack(">I", raw[offset:offset + 4])[0]
        kind = raw[offset + 4:offset + 8]
        payload = raw[offset + 8:offset + 8 + size]
        crc = struct.unpack(">I", raw[offset + 8 + size:offset + 12 + size])[0]
        assert zlib.crc32(kind + payload) & 0xffffffff == crc
        if kind == b"tEXt":
            metadata.append(payload.decode("latin1"))
        elif kind == b"zTXt":
            _, value = payload.split(b"\0", 1)
            metadata.append(zlib.decompress(value[1:]).decode("latin1"))
        elif kind == b"iTXt":
            keyword, value = payload.split(b"\0", 1)
            compressed, value = value[0], value[2:]
            _, _, value = value.split(b"\0", 2)
            metadata.append(keyword.decode("latin1") + (zlib.decompress(value) if compressed else value).decode("utf-8"))
        offset += size + 12
        if kind == b"IEND":
            ended = True
            break
    assert ended and offset == len(raw)
    return findings("\n".join(metadata))


def audit_tree(bundle):
    issues = []
    for path in sorted(p for p in bundle.rglob("*") if p.is_file()):
        relative = path.relative_to(bundle)
        if private_name(relative):
            issues.append({"file": relative.as_posix(), "type": "private_filename"})
            continue
        if path.suffix in TEXT or path.name == ".gitignore":
            text = decode(path.read_bytes())
            issues.extend({"file": relative.as_posix(), "type": kind} for kind in findings(text))
            if path.suffix == ".md":
                prose = re.sub(r"```.*?```", "", text, flags=re.S)
                for target in re.findall(r"\]\(([^)]+)\)", prose):
                    target = target.strip().strip("<>")
                    if re.match(r"^[A-Za-z]+:", target) or target.startswith("#"):
                        continue
                    local = unquote(target.split("#", 1)[0])
                    destination = (path.parent / local).resolve()
                    if not destination.is_relative_to(bundle.resolve()) or not destination.exists():
                        issues.append({"file": relative.as_posix(), "type": "missing_or_external_local_link"})
        if path.suffix in {".png", ".svg"}:
            issues.extend({"file": relative.as_posix(), "type": kind} for kind in image_check(path))
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"session11-\d{4}-\d{2}-\d{2}-[a-z0-9]+", args.run_id):
        parser.error("Expected a new session11 date/id")
    evidence = ROOT / "evidence" / args.run_id
    output = ROOT / "output" / "share" / args.run_id
    if evidence.exists() or output.exists():
        raise RuntimeError("Refusing to overwrite an earlier run")
    # Only enumerates nonignored names; does not read private/state files.
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", ROOT.name],
                            cwd=ROOT.parent, text=True, capture_output=True, check=True).stdout.splitlines()
    ignored = subprocess.run(["git", "check-ignore", "-q", "--", f"{ROOT.name}/output/share/probe.zip"], cwd=ROOT.parent)
    assert ignored.returncode == 0, "Export output must be ignored"
    sources, excluded = [], []
    for name in sorted(set(listed)):
        path = ROOT.parent / name
        rel = path.relative_to(ROOT)
        accepted = (rel == Path("README.md")
                    or (rel.parts[0] == "docs" and path.suffix == ".md")
                    or (rel.parts[0] == "infra" and (path.suffix == ".tf" or path.name == ".terraform.lock.hcl"))
                    or (rel.parts[0] in {"src", "tests", "scripts"} and path.suffix == ".py")
                    or (rel.parts[0] == "evidence" and path.suffix in {".json", ".txt", ".mmd"})
                    or (rel.parts[0] == "evidence" and rel.relative_to("evidence").as_posix() in REVIEWED_IMAGES))
        if accepted and not private_name(rel) and not path.is_symlink():
            sources.append(rel)
        else:
            excluded.append({"file": rel.as_posix(), "type": "outside_explicit_allowlist"})
    # Refuse any image newly added since the manual visual audit.
    actual_images = {p.relative_to(ROOT / "evidence").as_posix()
                     for p in (ROOT / "evidence").rglob("*") if p.suffix.lower() in {".png", ".svg", ".jpg", ".jpeg", ".webp"}}
    assert actual_images == set(REVIEWED_IMAGES), "Image inventory changed; manual review required"
    image_report = {"review": "12 PNG opened visually; SVG XML/source checked with its paired rendered PNG",
                    "limitations": "Manual review and metadata heuristics; not an absolute privacy guarantee",
                    "images": [{"file": f"evidence/{name}", "classification": "safe_for_this_scope",
                                "finding_type": "No private content observed; account/ARN/resource/workspace metadata may be retained",
                                "sha256": digest(ROOT / "evidence" / name)} for name in REVIEWED_IMAGES]}
    write_json(evidence / "image-review.json", image_report)
    sources.append((evidence / "image-review.json").relative_to(ROOT))
    allowlist = {"source_files": [p.as_posix() for p in sorted(sources)],
                 "excluded_nonignored": excluded, "ignored_private_files_opened": False,
                 "omitted": ["state/backups/plans", "private tfvars/email", "credentials/keys/.env", "provider/cache/deployment ZIP", "browser/auth/work files", "output", ".git"],
                 "generated_export_files": [".gitignore", "SHARE-NOTES.md", "PACKAGE-VERIFICATION.json", "MANIFEST.json", "SHA256SUMS.txt"],
                 "generated_evidence_files": ["allowlist.json", "local-tests.json"],
                 "source_result_not_archived": "export-result.json (contains final archive hash)"}
    write_json(evidence / "allowlist.json", allowlist)
    sources.append((evidence / "allowlist.json").relative_to(ROOT))
    bundle = output / "WS04-share"
    bundle.mkdir(parents=True)
    origins = {}
    for rel in sources:
        path = ROOT / rel
        target = bundle / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix in TEXT:
            problems = findings(decode(path.read_bytes()))
            if problems:
                raise RuntimeError(json.dumps({"file": rel.as_posix(), "finding_types": problems}))
        shutil.copyfile(path, target)
        origins[rel.as_posix()] = {"origin": "source_copy", "source_sha256": digest(path)}
    readme = bundle / "README.md"
    text = readme.read_text(encoding="utf-8")
    old = "Set-Location D:\\FCAJ-Workshops-2026\\ws04-Web_monitoring"
    assert old in text
    readme.write_text(text.replace(old, "# Mo PowerShell ngay trong thu muc WS04-share da giai nen"), encoding="utf-8")
    origins["README.md"]["origin"] = "export_only_workspace_command_adaptation"
    (bundle / ".gitignore").write_text((ROOT.parent / ".gitignore").read_text(encoding="utf-8") + "\n# Standalone export: keep local work/auth/share artifacts private.\noutput/\n", encoding="utf-8")
    (bundle / "SHARE-NOTES.md").write_text(
        "# Local share bundle\n\n"
        "Xem [project summary](docs/project-summary.md), [README](README.md) va [sharing review](docs/session-11-sharing-readiness.md).\n\n"
        "Ban nay khong co state, private email tfvars, credentials, auth/browser cache hay .git.\n"
        "Account ID/ARN/profile/resource names va workspace paths duoc giu lai nhu metadata.\n"
        "Khong thay account trong Terraform de tao an tuong portable: doc account guard truoc deployment.\n"
        "README chi doi lenh Set-Location cho thu muc giai nen; .gitignore doc lap them output/.\n"
        "Source, Terraform va evidence khac giu byte goc. Generated files duoc danh dau trong manifest.\n\n"
        "Chi test offline: `python -B -m unittest discover -s tests -v`. Khong can AWS credentials/boto3.\n"
        "scripts/session05*, session06*, session07*, session08* co the APPLY/INVOKE AWS/GUI EMAIL.\n"
        "Khong chay hang loat, khong tai su dung plan/hash lich su. Day la source doi chieu thuc nghiem.\n"
        "scripts/session09_review.py va session11_share_export.py chi local, can source Git workspace;\n"
        "chung khong phai buoc bat buoc de test bundle. Init providers/deployment khong duoc test o chang nay.\n"
        "Neu dung Git, khoi tao repository rieng truoc khi dung git check-ignore; bundle khong tu init Git.\n"
        "Email subscription khi trien khai moi can nguoi dung Confirm; khong sao chep subscription cu.\n\n"
        "Doc cac snapshot lich su cung verified-summary; intermediate errors/pending duoc giu nguyen.\n"
        "Mot anh session03 duoc nhac bang ten trong nhat ky cu khong co trong nguon; khong tai tao.\n"
        "Chua chon license/chua upload/chua kiem tra GitHub preview. Nguoi dung quyet dinh truoc public.\n"
        "Metrics/dashboard/alarm/SNS co the phat sinh chi phi; khong bao dam mien phi/credit.\n"
        "Cleanup rieng, chua chay. Anh da xem bang mat va text scan heuristic khong bao dam tuyet doi.\n",
        encoding="utf-8")
    tests = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
                           cwd=bundle, capture_output=True, text=True, encoding="utf-8", errors="replace")
    test_report = {"command": "python -B -m unittest discover -s tests -v", "location": "exported bundle",
                   "python_version": sys.version.split()[0], "exit_code": tests.returncode,
                   "stdout": tests.stdout, "stderr": tests.stderr, "aws_or_integration_commands_executed": False}
    write_json(evidence / "local-tests.json", test_report)
    test_rel = (evidence / "local-tests.json").relative_to(ROOT)
    shutil.copyfile(evidence / "local-tests.json", bundle / test_rel)
    origins[test_rel.as_posix()] = {"origin": "local_mock_test_evidence", "source_sha256": digest(evidence / "local-tests.json")}
    if tests.returncode:
        raise RuntimeError("Export mock tests failed; read local-tests.json")
    issues = audit_tree(bundle)
    if issues:
        raise RuntimeError(json.dumps(issues))
    # Public report contains no self-referential archive hash. External result does.
    verification = {"local_mock_tests_exit_code": 0, "local_mock_tests_count": 7,
                    "local_links_missing": 0, "privacy_heuristic_findings": [],
                    "visual_review_png_count": 12, "svg_xml_and_paired_png_checked": True,
                    "png_crc_and_metadata_checked": True, "all_original_image_hashes_preserved": True,
                    "aws_calls": 0, "integration_scripts_executed": False,
                    "github_preview_checked": False, "external_links_checked": False,
                    "deployment_from_fresh_checkout_checked": False,
                    "archive_crc_members_and_hashes_verified": False,
                    "scope": "Local file/link/hash review, mock tests, manual image audit; not a security certification"}
    report_path = bundle / "PACKAGE-VERIFICATION.json"
    archive = output / "WS04-share.zip"
    for pass_number in range(2):
        report_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        payload = sorted(p for p in bundle.rglob("*") if p.is_file() and p.name not in {"MANIFEST.json", "SHA256SUMS.txt"})
        entries = [{"path": p.relative_to(bundle).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p),
                    **origins.get(p.relative_to(bundle).as_posix(), {"origin": "generated_export_metadata"})} for p in payload]
        manifest = {"run_id": args.run_id, "files": entries,
                    "excluded_from_self_hash": ["MANIFEST.json", "SHA256SUMS.txt"],
                    "archive_hash": "Sibling WS04-share.zip.sha256; external export-result.json in source evidence"}
        (bundle / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        checksum_files = sorted(p for p in bundle.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
        (bundle / "SHA256SUMS.txt").write_text("".join(f"{digest(p)}  {p.relative_to(bundle).as_posix()}\n" for p in checksum_files), encoding="utf-8")
        expected = {p.relative_to(output).as_posix(): digest(p) for p in bundle.rglob("*") if p.is_file()}
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name in sorted(expected):
                z.write(output / name, arcname=name)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert len(z.namelist()) == len(expected) and set(z.namelist()) == set(expected)
            assert all(hashlib.sha256(z.read(name)).hexdigest() == sha for name, sha in expected.items())
        verification["archive_crc_members_and_hashes_verified"] = True
    assert not audit_tree(bundle), "Final generated content must pass the same privacy/link audit"
    for rel, details in origins.items():
        if details["origin"] != "export_only_workspace_command_adaptation":
            assert digest(bundle / rel) == details["source_sha256"], f"Unexpected source alteration: {rel}"
    # All exported files must have a declared source or one of the generated names.
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()}
    expected_paths = {p.as_posix() for p in sources} | {test_rel.as_posix()} | set(allowlist["generated_export_files"])
    assert actual == expected_paths, "Unexpected file escaped the allowlist"
    zip_hash = digest(archive)
    (output / "WS04-share.zip.sha256").write_text(f"{zip_hash}  WS04-share.zip\n", encoding="utf-8")
    result = {"run_id": args.run_id, "export_directory": f"output/share/{args.run_id}/WS04-share",
              "zip": f"output/share/{args.run_id}/WS04-share.zip", "zip_sha256": zip_hash,
              "files_including_manifest_checksums": len(actual), "source_inventory_matches_allowlist": True,
              "source_copies_and_original_evidence_unchanged": True,
              "manifest_sha256": digest(bundle / "MANIFEST.json"),
              "verification": verification, "excluded_nonignored": excluded}
    write_json(evidence / "export-result.json", result)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
