"""Enforce configured backend line/branch thresholds on measured coverage."""

import argparse
import json
from pathlib import Path

import yaml


def evaluate(report, config):
    if report.get("meta", {}).get("branch_coverage") is not True or not report.get(
        "files"
    ):
        raise ValueError("Nonempty branch coverage evidence is required")
    totals = report["totals"]
    rows = []
    for kind, covered_key, total_key in (
        ("line", "covered_lines", "num_statements"),
        ("branch", "covered_branches", "num_branches"),
    ):
        covered, total = totals[covered_key], totals[total_key]
        threshold = config["coverage"][kind]
        if (
            type(covered) is not int
            or type(total) is not int
            or total <= 0
            or not 0 <= covered <= total
            or type(threshold) not in (int, float)
            or not 0 <= threshold <= 100
        ):
            raise ValueError("Invalid coverage counts or configured threshold")
        percent = covered / total * 100
        rows.append(
            {
                "id": f"backend-{kind}-coverage",
                "family": "C01" if kind == "line" else "C02",
                "sev": "P0",
                "status": "pass" if percent >= threshold else "fail",
                "covered": covered,
                "total": total,
                "percent": round(percent, 3),
                "threshold": threshold,
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        rows = evaluate(
            json.loads(args.coverage.read_text(encoding="utf-8")),
            yaml.safe_load(args.config.read_text(encoding="utf-8")),
        )
        result = {"scope": "backend app only", "tests": rows}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError):
        # Do not echo malformed evidence/configuration, which may contain secrets.
        result = {
            "scope": "backend app only",
            "error": "Missing or invalid backend coverage evidence",
            "tests": [
                {
                    "id": "backend-coverage-evidence",
                    "family": "C00",
                    "sev": "P0",
                    "status": "notrun",
                }
            ],
        }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for row in result["tests"]:
        print(f"{row['id']}: {row['status']}")
    return 0 if all(row["status"] == "pass" for row in result["tests"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
