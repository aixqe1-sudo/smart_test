"""AST-based impact selection. Conservative by default, demonstrably imperfect in fast mode."""
from __future__ import annotations
import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def module_name(path: Path) -> str:
    return ".".join(path.with_suffix("").parts)

def direct_imports(path: Path) -> set[str]:
    try:
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports

def has_dynamic_import(path: Path) -> bool:
    try:
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if name in {"import_module", "__import__"}:
                return True
    return False

def all_tests() -> list[str]:
    return sorted(str(path.relative_to(ROOT)) for path in (ROOT / "tests").glob("test_*.py"))

def dependencies() -> tuple[dict[str, set[str]], bool]:
    """Return static transitive dependencies for each test; report dynamic imports anywhere."""
    paths = list((ROOT / "shop").glob("*.py")) + list((ROOT / "tests").glob("test_*.py"))
    graph = {module_name(path.relative_to(ROOT)): direct_imports(path.relative_to(ROOT)) for path in paths}
    dynamic = any(has_dynamic_import(path.relative_to(ROOT)) for path in paths)
    def visit(module: str, seen: set[str]):
        if module in seen: return
        seen.add(module)
        for imported in graph.get(module, set()):
            if imported in graph: visit(imported, seen)
    mapped = {}
    for test in all_tests():
        seen: set[str] = set()
        visit(module_name(Path(test)), seen)
        mapped[test] = seen
    return mapped, dynamic

def changed_files(base: str, include_worktree: bool = False) -> list[str]:
    """CI: diff from base to HEAD. Local: optionally include staged and unstaged changes."""
    command = ["git", "diff", "--name-only", "--diff-filter=ACMRT", f"{base}...HEAD"]
    try:
        result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        names = set(result.stdout.splitlines())
        if include_worktree:
            for args in (["git", "diff", "--name-only", "HEAD"],):
                names.update(subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True).stdout.splitlines())
        return sorted(names)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Cannot calculate Git diff: {exc.stderr.strip()}") from exc

def select(changed: list[str], mode: str = "safe") -> dict:
    tests = all_tests()
    changed = sorted(set(changed))
    result = {"mode": mode, "changed": changed, "selected": [], "total_tests_files": len(tests),
              "full_suite": False, "reason": "", "known_limitations": ["Runtime imports and config-driven dependencies may not appear in AST graph"]}
    if not changed:
        result.update(selected=tests, full_suite=True, reason="No changes supplied; avoid a false green")
        return result
    production = [x for x in changed if x.startswith("shop/") and x.endswith(".py")]
    changed_tests = [x for x in changed if x in tests]
    unknown = [x for x in changed if not (x in tests or (x.startswith("shop/") and x.endswith(".py")) or x.endswith(".md"))]
    if unknown:
        result.update(selected=tests, full_suite=True, reason="Unmapped changes: " + ", ".join(unknown))
        return result
    graph, dynamic = dependencies()
    if mode == "safe" and production and dynamic:
        result.update(selected=tests, full_suite=True, reason="Dynamic import detected; static graph cannot guarantee completeness")
        return result
    impacted = {module_name(Path(filename)) for filename in production}
    selected = set(changed_tests)
    for test, deps in graph.items():
        if deps.intersection(impacted):
            selected.add(test)
    # Unmapped source changes must NOT produce a green check with zero tests.
    if production and not selected:
        result.update(selected=tests, full_suite=True, reason="Changed source has no mapped tests")
    elif selected:
        result.update(selected=sorted(selected), reason="Static dependency impact analysis")
    else:
        result.update(selected=[], reason="Documentation-only change")
    return result

def main():
    parser = argparse.ArgumentParser(description="Select pytest files based on Git changes")
    parser.add_argument("--base", default="HEAD~1", help="Git merge base / revision for comparison")
    parser.add_argument("--mode", choices=["safe", "fast"], default="safe")
    parser.add_argument("--ai", action="store_true", help="Use local Ollama to add tests, never remove tests")
    parser.add_argument("--worktree", action="store_true", help="Include unstaged and staged working changes")
    parser.add_argument("--changed", nargs="*", help="Explicit changed paths (for experiments)")
    parser.add_argument("--output", default="reports/selection.json")
    args = parser.parse_args()
    try:
        result = select(args.changed if args.changed is not None else changed_files(args.base, args.worktree), args.mode)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.ai and not result["full_suite"] and result["selected"]:
        from tools.ai_advisor import advise
        try:
            suggested = advise(result["changed"], all_tests())
            result["ai_suggested"] = suggested
            result["selected"] = sorted(set(result["selected"]) | set(suggested))
            result["reason"] += "; Ollama recommendations added (advisory only)"
        except RuntimeError as exc:
            # If an explicitly requested advisor fails, don't turn uncertainty into green.
            result.update(selected=all_tests(), full_suite=True, reason=f"AI advisor unavailable: {exc}; full suite fallback")
    target = ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
