"""Scan candidate ancestry with pinned Gitleaks, retaining redacted local evidence."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    scanner = shutil.which("gitleaks")
    reason = None
    if scanner is None:
        reason = "Install official Gitleaks8.30.1 and put its executable on PATH"
    elif subprocess.check_output([scanner, "version"], text=True).strip() != "8.30.1":
        reason = "Expected reviewed Gitleaks8.30.1"
    elif os.environ.get("SOLAROPS_RELEASE_SOURCE_SHA", sha) != sha:
        reason = "Campaign source SHA does not match current source"
    folder = args.junit.parent
    folder.mkdir(parents=True, exist_ok=True)
    report = folder / "candidate-secret-history.json"
    report.unlink(missing_ok=True)
    if reason is None:
        command = [scanner, "git", str(root), "--log-opts=HEAD", "--redact",
                   "--report-format=json", f"--report-path={report}"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
        (folder / "candidate-secret-history.log").write_text(result.stdout + result.stderr)
        if result.returncode != 0:
            reason = f"Gitleaks exited{result.returncode}; inspect protected redacted report"
        elif not report.is_file() or json.loads(report.read_text()) != []:
            reason = "Missing or nonempty secret scan result"
    suite = ET.Element("testsuite", name="outgoing-secret-history", tests="1",
                       failures="1" if reason else "0")
    case = ET.SubElement(suite, "testcase", name="candidate_ancestry_has_no_detected_secrets",
                         classname="Z01.secret-history")
    if reason:
        ET.SubElement(case, "failure", message=reason).text = reason
    ET.ElementTree(suite).write(args.junit, encoding="utf-8", xml_declaration=True)
    print(reason or f"Candidate ancestry scan passed at{sha}")
    return 1 if reason else 0


if __name__ == "__main__":
    sys.exit(main())
