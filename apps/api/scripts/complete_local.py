"""Start the isolated complete candidate; never reset a database or stop other apps."""
import argparse
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "apps/api"
WEB = ROOT / "apps/web"
PYTHON = API / ".venv/bin/python"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["migrate", "seed", "serve"])
    parser.add_argument("--env", type=Path, default=ROOT / "var/complete-preview.env")
    parser.add_argument("--api-port", type=int, default=8061)
    parser.add_argument("--web-port", type=int, default=3061)
    args = parser.parse_args()
    if not all(1024 <= port <= 65535 for port in (args.api_port, args.web_port)):
        parser.error("Ports must be between 1024 and 65535")
    if args.api_port == args.web_port:
        parser.error("API and web ports must differ")
    values = dotenv_values(args.env, interpolate=False)
    env = {**os.environ, **{k: v for k, v in values.items() if v is not None}}
    url = make_url(env.get("SOLAROPS_DATABASE_URL", ""))
    if (env.get("SOLAROPS_APP_ENV") != "development"
            or url.host not in {"127.0.0.1", "localhost"}
            or not re.fullmatch(r"solarops_release_demo_[0-9]{8}", url.database or "")):
        parser.error("Requires development and an explicitly named local solarops_release_demo_XXXXXXXX database")
    if args.action == "migrate":
        return subprocess.call([str(PYTHON), "-m", "alembic", "upgrade", "head"], cwd=API, env=env)
    if args.action == "seed":
        for script in ["seed_release_preview.py", "seed_demo.py"]:
            subprocess.run([str(PYTHON), f"scripts/{script}"], cwd=API, env=env, check=True)
        return 0
    if not (WEB / ".next/BUILD_ID").is_file():
        parser.error("Run npm run build in apps/web first")
    # Check both listeners before starting either child. Never stop an existing service.
    for port in (args.api_port, args.web_port):
        with socket.socket() as listener:
            try:
                listener.bind(("127.0.0.1", port))
            except OSError:
                parser.error(f"Port {port} is unavailable; choose another port")
    children = []
    try:
        children.append(subprocess.Popen([str(API / ".venv/bin/uvicorn"), "app.main:app", "--host", "127.0.0.1", "--port", str(args.api_port)], cwd=API, env=env))
        deadline = time.monotonic() + 30
        while True:
            if children[0].poll() is not None:
                raise RuntimeError("Candidate API exited; check the selected API port and database configuration")
            try:
                with urlopen(f"http://127.0.0.1:{args.api_port}/api/v1/ready", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Candidate API readiness timed out") from None
                time.sleep(.25)
        children.append(subprocess.Popen(["node", "node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", str(args.web_port)], cwd=WEB, env={**env, "SOLAROPS_API_ORIGIN": f"http://127.0.0.1:{args.api_port}"}))
        deadline = time.monotonic() + 30
        while True:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("Candidate server exited before frontend readiness")
            try:
                with urlopen(f"http://127.0.0.1:{args.web_port}/login", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Candidate frontend readiness timed out") from None
                time.sleep(.25)
        print(f"API http://127.0.0.1:{args.api_port} | Web http://127.0.0.1:{args.web_port} | Ctrl-C stops these child processes only", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(.5)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


if __name__ == "__main__":
    sys.exit(main())
