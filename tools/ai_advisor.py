"""Optional local-model suggestion layer. AI can ADD test files; never remove baseline tests."""
from __future__ import annotations
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def advise(changed: list[str], candidates: list[str], model: str | None = None) -> list[str]:
    """Ask a local Ollama model for extra candidate tests. All returned paths are allowlisted."""
    model = model or os.environ.get("OLLAMA_MODEL")
    if not model:
        raise RuntimeError("Set OLLAMA_MODEL to an installed Ollama model to enable --ai")
    excerpts = {}
    for path in changed:
        file = ROOT / path
        if path.startswith("shop/") and file.is_file() and file.resolve().is_relative_to(ROOT):
            excerpts[path] = file.read_text(encoding="utf-8")[:4000]
    prompt = (
        "You are reviewing change-impact testing for an educational checkout app. "
        "Recommend EXTRA tests that might be affected by changed modules, including dynamic imports. "
        'Return JSON exactly like {"tests": ["tests/test_checkout.py"]}. '
        "Only use the listed candidate filenames. You may expand but never remove existing tests. "
        f"Changed files: {json.dumps(changed)}\n"
        f"Changed file contents: {json.dumps(excerpts)}\n"
        f"Candidate tests: {json.dumps(candidates)}\n"
    )
    payload = json.dumps({"model": model, "prompt": prompt, "format": "json", "stream": False}).encode()
    request = Request("http://127.0.0.1:11434/api/generate", data=payload,
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=45) as response:
            reply = json.load(response)
        data = json.loads(reply["response"])
        entries = data.get("tests", [])
        if not isinstance(entries, list):
            raise ValueError("Model returned invalid test list")
        return sorted({item for item in entries if isinstance(item, str) and item in candidates})
    except Exception as exc:
        raise RuntimeError(f"Local AI advisor unavailable or returned invalid JSON: {exc}") from exc
