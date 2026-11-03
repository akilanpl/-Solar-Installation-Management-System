"""Own live services for legacy campaigns; fail rather than reuse a preview.

Only CI's loopback PostgreSQL service is accepted. The browser database is
separate from pytest and created once by this invocation's workflow job.
"""
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "apps/api"


def wait_ready(url, process):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Owned release service exited; inspect its retained log")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, TimeoutError):
            pass
        time.sleep(0.2)
    raise RuntimeError("Owned release service readiness timed out")


def main():
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("Release environment requires a fresh GitHub-hosted job")
    if (ROOT / ".env").exists():
        raise ValueError("Release CI must not load a private checkout environment")
    test_url = make_url(os.environ["SOLAROPS_TEST_DATABASE_URL"])
    if test_url.host not in {"localhost", "127.0.0.1"} or test_url.database != "solarops_test":
        raise ValueError("Requires workflow-owned loopback solarops_test PostgreSQL")
    for port in (3061, 8061):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))  # Occupied listeners are preserved.
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    folder = ROOT / "var/release-campaign" / sha
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder.chmod(0o700)
    env = dict(os.environ)
    env.update(SOLAROPS_APP_ENV="development", SOLAROPS_RELEASE_DATABASE_OWNED="true",
        SOLAROPS_DATABASE_URL=test_url.set(database="solarops_browser_release_ci").render_as_string(hide_password=False),
        SOLAROPS_RELEASE_FIXTURE_DIR=str(folder),
        SOLAROPS_EVIDENCE_DIR=str(folder / "uploads"), SOLAROPS_MAILBOX_PATH=str(folder / "mailbox.jsonl"),
        SOLAROPS_TRUSTED_ORIGINS="http://127.0.0.1:3061",
        SOLAROPS_WEBAUTHN_RP_ID="127.0.0.1", SOLAROPS_WEBAUTHN_ALLOWED_ORIGINS="http://127.0.0.1:3061",
        SOLAROPS_API_ORIGIN="http://127.0.0.1:8061", SOLAROPS_WEB_URL="http://127.0.0.1:3061",
        NEXT_PUBLIC_SOLAROPS_ENV="development", NEXT_TELEMETRY_DISABLED="1",
        SOLAROPS_LOGIN_IP_LIMIT="1000", SOLAROPS_LOGIN_IDENTIFIER_LIMIT="1000")
    for key in ("SOLAROPS_RAZORPAY_KEY_ID", "SOLAROPS_RAZORPAY_KEY_SECRET", "SOLAROPS_RAZORPAY_WEBHOOK_SECRET", "SOLAROPS_SMTP_HOST"):
        if env.get(key):
            raise ValueError("External integrations forbidden in release campaigns")
    stamp = folder / "owned-environment.json"
    run = os.environ["GITHUB_RUN_ID"] + "/" + os.environ["GITHUB_RUN_ATTEMPT"]
    if stamp.exists():
        saved = json.loads(stamp.read_text())
        if saved["sha"] != sha or saved["run"] != run:
            raise ValueError("Release environment belongs to a different run/source")
        env["SOLAROPS_SEED_PASSWORD"] = saved["password"]
    else:
        env["SOLAROPS_SEED_PASSWORD"] = secrets.token_urlsafe(24)
        engine = create_engine(test_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
        try:
            with engine.connect() as connection:
                # Never DROP/reuse a database: an existing name fails CREATE.
                connection.execute(text("CREATE DATABASE solarops_browser_release_ci"))
        finally:
            engine.dispose()
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=API, env=env, check=True)
        subprocess.run([sys.executable, "scripts/prepare_release_campaign.py"], cwd=API, env=env, check=True)
        with os.fdopen(os.open(stamp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
            output.write(json.dumps({"sha": sha, "run": run, "password": env["SOLAROPS_SEED_PASSWORD"]}))
    def terminate(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    processes = []
    try:
        for name, command, cwd, url in [
            ("api", [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8061"], API, "http://127.0.0.1:8061/api/v1/ready"),
            ("web", ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", "3061"], ROOT / "apps/web", "http://127.0.0.1:3061/login"),
        ]:
            with (folder / f"{Path(sys.argv[1]).stem}-{name}.log").open("w") as log:
                process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
            processes.append(process)
            wait_ready(url, process)
        # Assertions execute unchanged against actual API/Next/PostgreSQL.
        return subprocess.call(["node", ".pushgate/campaigns/browser_campaign.cjs", *sys.argv[1:]],
            cwd=ROOT, env={**env, "SOLAROPS_RELEASE_SERVICES_READY": "true"})
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
