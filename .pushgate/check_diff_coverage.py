"""Enforce changed backend statement coverage against the actual PR merge base."""

import argparse
import json
import math
import re
import subprocess
from pathlib import Path

import yaml


def changed_lines(diff):
    files = {}
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            files.setdefault(current, set())
        elif line.startswith("@@ ") and current:
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            if not match:
                raise ValueError("Invalid diff hunk")
            start, count = int(match[1]), int(match[2] or 1)
            files[current].update(range(start, start + count))
    return files


def evaluate(files, coverage, threshold):
    if (
        type(threshold) not in (int, float)
        or not math.isfinite(threshold)
        or not 0 <= threshold <= 100
    ):
        raise ValueError("Invalid diff threshold")
    measured = {
        "apps/api/" + key.replace("\\", "/"): value
        for key, value in coverage["files"].items()
    }
    covered = total = 0
    absent = []
    for name, additions in files.items():
        if (
            not name.startswith("apps/api/app/")
            or not name.endswith(".py")
            or not additions
        ):
            continue
        if name not in measured:
            absent.append(name)
            continue
        data = measured[name]
        executed = set(data["executed_lines"])
        missing = set(data["missing_lines"])
        statements = additions & (executed | missing)
        covered += len(statements & executed)
        total += len(statements)
    passed = not absent and (total == 0 or covered / total * 100 >= threshold)
    return {
        "id": "backend-diff-coverage",
        "family": "C03",
        "sev": "P0",
        "status": "pass" if passed else "fail",
        "covered": covered,
        "total": total,
        "percent": round(covered / total * 100, 3) if total else None,
        "threshold": threshold,
        "unmeasured_files": absent,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        merge_base = subprocess.check_output(
            ["git", "merge-base", args.base, "HEAD"], text=True
        ).strip()
        diff = subprocess.check_output(
            [
                "git",
                "-c",
                "core.quotePath=false",
                "diff",
                "--no-renames",
                "--unified=0",
                f"{merge_base}..HEAD",
                "--",
                "apps/api/app",
            ],
            text=True,
            encoding="utf-8",
        )
        row = evaluate(
            changed_lines(diff),
            json.loads(args.coverage.read_text(encoding="utf-8")),
            yaml.safe_load(args.config.read_text(encoding="utf-8"))["coverage"]["diff"],
        )
        report = {"base": merge_base, "tests": [row]}
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.CalledProcessError,
        yaml.YAMLError,
    ):
        report = {
            "error": "Missing or invalid diff coverage evidence/base",
            "tests": [
                {
                    "id": "backend-diff-coverage",
                    "family": "C03",
                    "sev": "P0",
                    "status": "notrun",
                }
            ],
        }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"backend-diff-coverage: {report['tests'][0]['status']}")
    return 0 if report["tests"][0]["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
