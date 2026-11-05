"""Reproduce a missed regression in an isolated copy, without changing the original checkout."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def invoke(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)

def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai-x-qe-lab-") as tmp:
        root = Path(tmp)
        for name in ("shop", "tests", "tools"):
            shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(ROOT / "pyproject.toml", root / "pyproject.toml")
        baseline = invoke(sys.executable, "-m", "pytest", "-q", cwd=root)
        risk = root / "shop/risk.py"
        risk.write_text(risk.read_text().replace("return amount <= 500", "return True"), encoding="utf-8")
        results = {"experiment": "Injected regression: risk permits orders over 500", "baseline_exit": baseline.returncode,
                   "baseline_tail": baseline.stdout.strip().splitlines()[-1:]}
        for mode in ("fast", "safe"):
            selector = invoke(sys.executable, "-m", "tools.selector", "--mode", mode, "--changed", "shop/risk.py", cwd=root)
            data = json.loads((root / "reports/selection.json").read_text())
            selected = invoke(sys.executable, "-m", "tools.run_selected", cwd=root)
            results[mode] = {"selected": data["selected"], "selection_reason": data["reason"],
                             "selected_exit": selected.returncode, "selected_tail": (selected.stdout+selected.stderr).strip().splitlines()[-4:]}
        full = invoke(sys.executable, "-m", "pytest", "-q", cwd=root)
        results["full_suite"] = {"exit": full.returncode, "tail": (full.stdout + full.stderr).strip().splitlines()[-7:]}
        output = ROOT / "reports/demo-results.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(results, indent=2))
        valid = (results["baseline_exit"] == 0 and results["fast"]["selected_exit"] == 0 and
                 results["safe"]["selected_exit"] != 0 and results["full_suite"]["exit"] != 0)
        print("\nDEMO VERIFIED" if valid else "\nDEMO DID NOT MATCH EXPECTED OUTCOMES")
        return 0 if valid else 1

if __name__ == "__main__":
    raise SystemExit(main())
