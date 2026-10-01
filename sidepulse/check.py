"""Test the chezmoi-managed SidePulse files in a temporary package copy."""

import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import sidepulse


def main():
    source = Path(__file__).resolve().parent
    manifest = json.loads((source / "upstream.json").read_text())
    version = importlib.metadata.version("sidepulse")
    if version != manifest["version"]:
        raise SystemExit(f"Expected SidePulse {manifest['version']}; installed: {version}")
    package = Path(sidepulse.__file__).resolve().parent
    relative = Path("share/sidepulse/venv/lib/python3.13/site-packages/sidepulse")
    expected_package = (Path.home() / ".local" / relative).resolve()
    if package != expected_package:
        raise SystemExit(f"Expected package at {expected_package}; imported: {package}")
    managed = source.parent / "chezmoi/dot_local" / relative
    files = [managed / name for name in manifest["managed_files"]]
    for path in files:
        if not path.is_file():
            raise SystemExit(f"Missing chezmoi source: {path}")
    print(f"SidePulse {version}: testing {len(files)} chezmoi-managed files", flush=True)

    with tempfile.TemporaryDirectory(prefix="sidepulse-check-") as directory:
        target = Path(directory)
        shutil.copytree(package, target / "sidepulse", ignore=shutil.ignore_patterns("__pycache__"))
        for path in files:
            shutil.copyfile(path, target / "sidepulse" / path.name)
        for test in (source / "tests").glob("test_*.py"):
            shutil.copy2(test, target / test.name)
        return subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-v", "-s", str(target)],
            cwd=target,
            env={**os.environ, "PYTHONPATH": str(target)},
            check=False,
        ).returncode


if __name__ == "__main__":
    sys.exit(main())
