"""Measure changed executable lines from this gate's fresh coverage database.

No caller-supplied mutation JSON is accepted. Until an isolated executable
mutation runner is reviewed/provisioned, mutation remains an explicit failure.
"""

import argparse
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import coverage


def git(root, *args):
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, timeout=45
    ).strip()


def verify_source(root):
    sha = git(root, "rev-parse", "HEAD")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Coverage campaign requires the exact clean committed source")
    live = git(root, "ls-remote", "origin", "refs/heads/main").split()
    if len(live) != 2 or live[1] != "refs/heads/main":
        raise ValueError("Live origin/main could not be verified")
    if live[0] != git(root, "rev-parse", "origin/main"):
        raise ValueError(
            "Cached origin/main differs from live origin/main; fetch and rerun"
        )
    return sha, live[0]


def changed_lines(root, base):
    result = {}
    current = None
    diff = git(
        root,
        "diff",
        "--no-ext-diff",
        "--unified=0",
        f"{base}...HEAD",
        "--",
        "apps/api/app",
    )
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("+++ /dev/null"):
            current = None
        elif current and line.startswith("@@"):
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            if not match:
                raise ValueError("Unrecognized Git diff hunk")
            start, count = int(match[1]), int(match[2] or 1)
            result.setdefault(current, set()).update(range(start, start + count))
    return result


def measured_diff(root, folder, sha, base):
    data_file = folder / "backend.coverage"
    exported = folder / "backend-coverage.json"
    log = folder / "backend.log"
    junit = folder / "backend.xml"
    for path in (data_file, exported, log, junit):
        if not path.is_file() or time.time() - path.stat().st_mtime > 3600:
            raise ValueError(
                f"Missing/stale fresh gate evidence: {path.name}; rerun full gate"
            )
    header = json.loads(log.read_text().splitlines()[0])
    if header.get("sha") != sha or "coverage" not in header.get("command", []):
        raise ValueError(
            "Backend campaign log is not bound to the current SHA and coverage command"
        )
    cases = list(ET.parse(junit).iter("testcase"))
    if not cases or any(
        c.find("failure") is not None
        or c.find("error") is not None
        or c.find("skipped") is not None
        for c in cases
    ):
        raise ValueError("Fresh full backend campaign did not pass without skips")
    cov = coverage.Coverage(
        data_file=str(data_file), source=[str(root / "apps/api/app")], branch=True
    )
    cov.load()
    if not cov.get_data().has_arcs():
        raise ValueError("Coverage database contains no branch measurements")
    # Re-export from the SQLite data, rather than trusting supplied percentages.
    regenerated = folder / "coverage-quality-remeasured.json"
    cov.json_report(outfile=str(regenerated))
    fresh = json.loads(regenerated.read_text())
    if fresh["totals"] != json.loads(exported.read_text())["totals"]:
        raise ValueError(
            "Backend JSON totals differ from this gate's measured coverage database"
        )
    measured = {Path(path).resolve() for path in cov.get_data().measured_files()}
    rows = []
    covered = total = 0
    for relative, changed in changed_lines(root, base).items():
        if not relative.endswith(".py"):
            continue
        path = (root / relative).resolve()
        _, statements, _, missing, _ = cov.analysis2(str(path))
        executable = set(statements) & changed
        if executable and path not in measured:
            raise ValueError(
                f"Changed executable module absent from measurements: {relative}"
            )
        hits = executable - set(missing)
        covered += len(hits)
        total += len(executable)
        rows.append(
            {
                "path": relative,
                "covered": len(hits),
                "total": len(executable),
                "missing_changed_lines": sorted(executable & set(missing)),
            }
        )
    percent = 100.0 if total == 0 else 100.0 * covered / total
    return {
        "sha": sha,
        "base_sha": base,
        "covered": covered,
        "total": total,
        "percent": percent,
        "threshold": 90,
        "files": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    args.junit.parent.mkdir(parents=True, exist_ok=True)
    failures = {}
    detail = None
    try:
        sha, base = verify_source(root)
        expected = root / ".pushgate/reports" / sha
        if args.junit.resolve().parent != expected.resolve():
            raise ValueError(
                "JUnit output must be in the current exact-SHA gate directory"
            )
        detail = measured_diff(root, expected, sha, base)
        (expected / "diff-coverage-measured.json").write_text(
            json.dumps(detail, indent=2) + "\n"
        )
        if detail["percent"] < 90:
            failures["diff_coverage_at_least_90"] = (
                f"Measured changed-line coverage {detail['percent']:.3f}% <90%; see diff-coverage-measured.json"
            )
    except (
        OSError,
        ValueError,
        KeyError,
        subprocess.SubprocessError,
        coverage.CoverageException,
        ET.ParseError,
    ) as error:
        failures["diff_coverage_at_least_90"] = (
            f"Fresh diff coverage unavailable: {type(error).__name__}: {error}"
        )
    failures["mutation_score_at_least_60"] = (
        "No reviewed isolated executable mutation runner is provisioned. A >=60% mutation score "
        "has NOT been measured. Install/pin a mutation engine and implement a serial campaign "
        "in a separate checkout with its own disposable PostgreSQL database; rerun actual tests "
        "per mutant and distinguish killed/survived/timeout/error. External result JSON is not proof."
    )
    suite = ET.Element(
        "testsuite",
        name="mutation-diff-coverage",
        tests="2",
        failures=str(len(failures)),
    )
    for name in ("diff_coverage_at_least_90", "mutation_score_at_least_60"):
        case = ET.SubElement(
            suite, "testcase", name=name, classname="S03.coverage-quality"
        )
        if name in failures:
            ET.SubElement(case, "failure", message=failures[name]).text = failures[name]
    ET.ElementTree(suite).write(args.junit, encoding="utf-8", xml_declaration=True)
    for reason in failures.values():
        print(reason)
    return 1 if failures else 0


def self_test():
    """Parser/negative-evidence selftests; never emitted as release JUnit."""
    import tempfile
    import unittest
    from unittest.mock import patch

    class Checks(unittest.TestCase):
        def test_changed_lines_exclude_deletions_and_include_new_ranges(self):
            diff = "+++ b/apps/api/app/example.py\n@@ -1,2 +2,3 @@\n@@ -9 +12,0 @@\n"
            with patch(__name__ + ".git", return_value=diff):
                self.assertEqual(
                    changed_lines(Path("."), "base"),
                    {"apps/api/app/example.py": {2, 3, 4}},
                )

        def test_missing_fresh_measurements_fail(self):
            with (
                tempfile.TemporaryDirectory() as directory,
                self.assertRaisesRegex(ValueError, "Missing/stale"),
            ):
                measured_diff(Path(directory), Path(directory), "a" * 40, "b" * 40)

    outcome = unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    )
    return 0 if outcome.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main())
