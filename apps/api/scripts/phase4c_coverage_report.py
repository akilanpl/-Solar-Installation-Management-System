"""Report measured Phase 4C and changed executable line coverage without relaxing gates."""

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "26a5f129e1eeea5ad772ab4e1b8c5f8f6d43bc3d"


def totals(files):
    statements = sum(f["summary"]["num_statements"] for f in files)
    covered = sum(f["summary"]["covered_lines"] for f in files)
    branches = sum(f["summary"]["num_branches"] for f in files)
    covered_branches = sum(f["summary"]["covered_branches"] for f in files)
    return {
        "covered_lines": covered,
        "statements": statements,
        "line_percent": round(100 * covered / statements, 3) if statements else None,
        "covered_branches": covered_branches,
        "branches": branches,
        "branch_percent": round(100 * covered_branches / branches, 3) if branches else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.coverage.read_text())
    diff = subprocess.run(
        ["git", "diff", "--unified=0", BASE, "--", "apps/api/app"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    added = {}
    file = None
    cursor = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            file = line[6:]
            continue
        hunk = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk:
            cursor = int(hunk.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            added.setdefault(file, set()).add(cursor)
            cursor += 1
        elif line.startswith(" ") and not line.startswith("---"):
            cursor += 1
    count = covered = 0
    missing = {}
    for name, lines in added.items():
        relative = name.removeprefix("apps/api/")
        coverage = report["files"].get(relative)
        if coverage is None:
            raise RuntimeError(f"Missing measured coverage for {relative}")
        executable = set(coverage["executed_lines"]) | set(coverage["missing_lines"])
        changed = lines & executable
        uncovered = changed & set(coverage["missing_lines"])
        count += len(changed)
        covered += len(changed) - len(uncovered)
        if uncovered:
            missing[relative] = sorted(uncovered)
    result = {
        "base_sha": BASE,
        "scope": "actual changed executable backend app lines; no exclusions or threshold changes",
        "whole_backend": totals(list(report["files"].values())),
        "finance_files": totals(
            [
                v
                for k, v in report["files"].items()
                if k
                in (
                    "app/models/finance.py",
                    "app/schemas/finance.py",
                    "app/services/finance_service.py",
                    "app/api/v1/finance.py",
                )
            ]
        ),
        "changed_executable_lines": count,
        "changed_covered_lines": covered,
        "diff_line_percent": round(100 * covered / count, 3) if count else None,
        "missing_changed_lines": missing,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "missing_changed_lines"}, indent=2))


if __name__ == "__main__":
    main()
