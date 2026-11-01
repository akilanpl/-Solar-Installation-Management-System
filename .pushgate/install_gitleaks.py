"""Install the pinned upstream scanner after verifying its published SHA256."""

import hashlib
import io
import os
import platform
import tarfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "8.30.1"
BASE = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}"


def main():
    if platform.machine().lower() not in {"amd64", "x86_64"}:
        raise SystemExit("This installer supports x64 Windows and Linux only")
    system = platform.system().lower()
    if system not in {"windows", "linux"}:
        raise SystemExit("Unsupported scanner platform")
    extension = "zip" if system == "windows" else "tar.gz"
    asset = f"gitleaks_{VERSION}_{system}_x64.{extension}"
    request_headers = {"User-Agent": "SolarOps-CI"}

    def download(name):
        request = urllib.request.Request(f"{BASE}/{name}", headers=request_headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()

    checksums = download(f"gitleaks_{VERSION}_checksums.txt").decode("utf-8")
    expected = next(
        line.split()[0] for line in checksums.splitlines() if line.split()[-1] == asset
    )
    archive = download(asset)
    if hashlib.sha256(archive).hexdigest() != expected:
        raise SystemExit("Scanner checksum mismatch; refusing installation")
    binary_name = "gitleaks.exe" if system == "windows" else "gitleaks"
    if system == "windows":
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            binary = bundle.read(binary_name)
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            member = bundle.extractfile(binary_name)
            if member is None:
                raise SystemExit("Missing scanner executable")
            binary = member.read()
    destination = Path(__file__).resolve().parents[1] / "var/tools" / binary_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(binary)
    if os.name != "nt":
        destination.chmod(0o755)
    print(f"Installed Gitleaks {VERSION}; verified upstream archive SHA256 {expected}")


if __name__ == "__main__":
    main()
