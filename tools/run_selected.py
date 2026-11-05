"""Run selected tests. Exit status propagates to CI."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(selection: dict) -> int:
    selected = selection["selected"]
    if not selected:
        print("No test execution required (documentation-only changes).")
        return 0
    return subprocess.call([sys.executable, "-m", "pytest", *selected], cwd=ROOT)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", default="reports/selection.json")
    args = parser.parse_args()
    return run(json.loads((ROOT / args.selection).read_text(encoding="utf-8")))

if __name__ == "__main__":
    raise SystemExit(main())
