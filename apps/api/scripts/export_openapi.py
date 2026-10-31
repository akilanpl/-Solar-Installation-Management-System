"""Write the live FastAPI OpenAPI document.

This imports the application and asks FastAPI for the schema of routes that
actually exist. It does not add planned endpoints.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.main import app  # noqa: E402


def main() -> None:
    destination = REPO_ROOT / "contracts" / "generated" / "openapi.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    spec = app.openapi()
    destination.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
