"""Deterministic skill formula; absent families receive no credit."""
import json
import sys
from pathlib import Path

W = {"S":5,"B":14,"A":12,"D":6,"F":8,"E":10,"X":8,"V":7,"Z":12,"P":5,"R":5,"C":3,"Y":3,"O":2}
SEV = {"P0":3, "P1":2, "P2":1}
VAL = {"pass":1.0, "flaky":0.5, "fail":0.0, "skip":0.0, "notrun":0.0}

def score(tests):
    result = 0
    for group, weight in W.items():
        rows = [t for t in tests if t["family"].startswith(group)]
        den = sum(SEV[t["sev"]] for t in rows)
        result += weight / sum(W.values()) * 100 * (sum(SEV[t["sev"]] * VAL[t["status"]] for t in rows) / den if den else 0)
    if any(t["sev"] == "P0" and t["status"] != "pass" for t in tests):
        result = min(result, 69)
    return round(result, 1)

if __name__ == "__main__":
    report = json.loads(Path(sys.argv[1]).read_text())
    report["score"] = score(report["tests"])
    # No complete-campaign claim while mandatory families/coverage/security are missing.
    executed = [t for t in report["tests"] if t["status"] in {"pass", "fail", "flaky"}]
    report["decision"] = "INCOMPLETE" if report["missing_evidence"] else (
        "PASS" if report["score"] >= 90 and len(executed) >= 100 and all(t["status"] == "pass" for t in report["tests"]) else "FAIL")
    Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + "\n")
    print(f'{report["decision"]}: {report["score"]}/100; see missing_evidence')
    sys.exit(0 if report["decision"] == "PASS" else 1)
