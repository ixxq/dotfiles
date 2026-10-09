"""Check the chezmoi INIT.LED script against a temporary drive, never hardware."""

from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix="sidepulse device check ") as directory:
        temporary = Path(directory)
        source = temporary / "source"
        source.mkdir()
        asset = source / ".chezmoitemplates/sidepulse/INIT.LED"
        asset.parent.mkdir(parents=True)
        shutil.copyfile(root / "chezmoi/.chezmoitemplates/sidepulse/INIT.LED", asset)
        target = temporary / "drive/INIT.LED"
        template = (root / "chezmoi/run_after_sidepulse-init.sh.tmpl").read_text()
        assert template.count("/Volumes/SidePulse/INIT.LED") == 1
        (source / "run_after_sidepulse-init.sh.tmpl").write_text(
            template.replace("/Volumes/SidePulse/INIT.LED", str(target))
        )
        home = temporary / "home"
        home.mkdir()
        command = ["chezmoi", "--config", "/dev/null", "--config-format", "toml", "--source", str(source),
                   "--destination", str(home), "--persistent-state", str(temporary / "state.db"), "apply"]
        subprocess.run(command, check=True)
        assert not target.parent.exists()
        target.parent.mkdir()
        original = (root / "sidepulse/defaults/INIT.LED").read_bytes()
        target.write_bytes(original)
        subprocess.run(command, check=True)
        assert target.read_bytes() == asset.read_bytes()
        modified = target.stat().st_mtime_ns
        subprocess.run(command, check=True)
        assert target.stat().st_mtime_ns == modified
        target.write_bytes(original)
        subprocess.run(command, check=True)
        assert target.read_bytes() == asset.read_bytes()
        expected = target.read_bytes()
        asset.unlink()
        assert subprocess.run(command, capture_output=True, text=True).returncode != 0
        assert target.read_bytes() == expected
    print("INIT.LED: disconnected, update, unchanged, drift and failure checks passed.")


if __name__ == "__main__":
    main()
