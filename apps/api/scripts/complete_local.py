"""Start the isolated complete candidate; never reset a database or stop other apps."""
import argparse
import os
import re
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
    args = parser.parse_args()
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
    children = []
    try:
        children.append(subprocess.Popen([str(API / ".venv/bin/uvicorn"), "app.main:app", "--host", "127.0.0.1", "--port", "8061"], cwd=API, env=env))
        deadline = time.monotonic() + 30
        while True:
            if children[0].poll() is not None:
                raise RuntimeError("Candidate API exited; check port 8061 and database configuration")
            try:
                with urlopen("http://127.0.0.1:8061/api/v1/ready", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Candidate API readiness timed out") from None
                time.sleep(.25)
        children.append(subprocess.Popen(["node", "node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", "3061"], cwd=WEB, env={**env, "SOLAROPS_API_ORIGIN": "http://127.0.0.1:8061"}))
        print("API http://127.0.0.1:8061 | Web http://127.0.0.1:3061 | Ctrl-C stops these child processes only", flush=True)
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
