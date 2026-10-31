"""Restrict local generated credentials to the current OS account."""

import os
import subprocess
from pathlib import Path


def protect(path: Path) -> None:
    if os.name == "nt":
        account = f"{os.environ['USERDOMAIN']}\\{os.environ['USERNAME']}"
        permissions = f"{account}:(OI)(CI)F" if path.is_dir() else f"{account}:F"
        subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", permissions],
            check=True,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        path.chmod(0o700 if path.is_dir() else 0o600)
