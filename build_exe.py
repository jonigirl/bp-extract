"""Build script for BP Extract distributable executables.

Usage:
    uv run python build_exe.py            # build both GUI and CLI
    uv run python build_exe.py --gui-only # build GUI only
    uv run python build_exe.py --cli-only # build CLI only
"""

import argparse
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"

EXCLUDE_DIRS = {".venv", ".git", "dist", "build", "__pycache__"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDE_FILES = {"config.json", "blueprints.json"}


def read_version() -> str:
    with open(ROOT / "pyproject.toml", "rb") as fh:
        data = tomllib.load(fh)
    return data["project"]["version"]


def run_pyinstaller(spec: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", spec],
        check=True,
        cwd=ROOT,
    )


def create_source_zip(version: str) -> Path:
    zip_path = DIST / f"BP.Extract.v{version}.source.zip"
    DIST.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in ROOT.rglob("*"):
            # Skip excluded top-level directories
            parts = path.relative_to(ROOT).parts
            if parts and parts[0] in EXCLUDE_DIRS:
                continue
            # Skip excluded file names
            if path.name in EXCLUDE_FILES:
                continue
            # Skip excluded suffixes
            if path.suffix in EXCLUDE_SUFFIXES:
                continue
            # Only add files
            if path.is_file():
                zf.write(path, path.relative_to(ROOT))

    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build BP Extract distributables.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gui-only", action="store_true", help="Build GUI exe only.")
    group.add_argument("--cli-only", action="store_true", help="Build CLI exe only.")
    args = parser.parse_args()

    version = read_version()
    print(f"Building BP Extract v{version}\n")

    build_gui = not args.cli_only
    build_cli = not args.gui_only

    if build_gui:
        print("--- Building GUI (onedir) ---")
        run_pyinstaller("bp_extract_gui.spec")

    if build_cli:
        print("--- Building CLI (onefile) ---")
        run_pyinstaller("bp_extract_cli.spec")

    print("--- Creating source zip ---")
    source_zip = create_source_zip(version)

    print("\nOutput files:")
    if build_gui:
        gui_dir = DIST / "BP Extract"
        gui_exe = gui_dir / "BP Extract.exe"
        print(f"  GUI dir : {gui_dir}")
        print(f"  GUI exe : {gui_exe}")
    if build_cli:
        cli_exe = DIST / "BP Extract CLI.exe"
        print(f"  CLI exe : {cli_exe}")
    print(f"  Source  : {source_zip}")


if __name__ == "__main__":
    main()
