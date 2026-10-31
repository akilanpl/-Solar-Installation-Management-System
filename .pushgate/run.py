"""Execute available checks, retain logs and block while campaign gaps remain."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

root = Path.cwd()
sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
folder = root / ".pushgate/reports" / sha
folder.mkdir(parents=True, exist_ok=True)
tests = []
stages = [
    ("lint-api", "S02", "P1", "apps/api", [".venv/bin/ruff", "check", "app", "tests", "scripts"]),
    ("backend", "B03", "P0", "apps/api", [".venv/bin/pytest", f"--junitxml={folder}/backend.xml"]),
    ("frontend", "F01", "P1", "apps/web", ["npm", "test", "--", "--reporter=junit", f"--outputFile={folder}/frontend.xml"]),
    ("typecheck", "S03", "P0", "apps/web", ["npm", "run", "typecheck"]),
    ("lint-web", "S02", "P1", "apps/web", ["npm", "run", "lint"]),
    ("build", "S01", "P0", "apps/web", ["npm", "run", "build"]),
    ("dependency-audit", "S06", "P0", "apps/web", ["npm", "audit", "--audit-level=high", "--json"]),
]
started = time.monotonic()
for name, family, sev, directory, command in stages:
    print(f"Running {name}", flush=True)
    with (folder / f"{name}.log").open("w") as log:
        try:
            outcome = subprocess.run(command, cwd=root / directory, stdout=log, stderr=subprocess.STDOUT, timeout=600)
            status = "pass" if outcome.returncode == 0 else "fail"
        except (OSError, subprocess.TimeoutExpired):
            status = "notrun"
    xml = folder / f"{name}.xml"
    if xml.exists():
        for item in ET.parse(xml).iter("testcase"):
            state = "fail" if item.find("failure") is not None or item.find("error") is not None else "skip" if item.find("skipped") is not None else "pass"
            name_value = item.get("name", "")
            assigned = family
            if name == "backend":
                assigned = "D01" if "migration" in name_value or "database" in name_value else "Z01" if "otp" in name_value or "unauthorized" in name_value else "A01" if "health" in name_value or "readiness" in name_value else "B03"
            tests.append({"id": name_value, "family": assigned, "sev": sev, "status": state})
    else:
        tests.append({"id": name, "family": family, "sev": sev, "status": status})
missing = ["Full customer-to-warranty browser journey", "Load, resilience and accessibility campaign", "Mutation, diff and branch coverage", "Secret scan of all outgoing commits", "Main baseline ratchet and two-order CI run", "Phase 3 partial delivery/returns/procurement/scheduling/serial warranty requirements"]
for family in "DEXVZPRCYO":
    tests.append({"id": f"mandatory-{family}-campaign", "family": f"{family}00", "sev": "P0", "status": "notrun"})
report = {"sha": sha, "seed": 20261031, "duration_seconds": round(time.monotonic() - started, 2), "tests": tests, "missing_evidence": missing}
path = folder / "report.json"
path.write_text(json.dumps(report, indent=2) + "\n")
result = subprocess.run([sys.executable, ".pushgate/score.py", str(path)], check=False)
print(f"Evidence: {folder}")
sys.exit(result.returncode)
