from tools.selector import select

def test_fast_selects_only_direct_risk_test():
    result = select(["shop/risk.py"], mode="fast")
    assert result["selected"] == ["tests/test_risk.py"]

def test_safe_mode_falls_back_to_all_tests_on_dynamic_import():
    result = select(["shop/risk.py"], mode="safe")
    assert result["full_suite"]
    assert "tests/test_checkout.py" in result["selected"]

def test_cart_impacts_checkout_and_pricing():
    result = select(["shop/cart.py"], mode="fast")
    assert {"tests/test_cart.py", "tests/test_checkout.py", "tests/test_pricing.py"}.issubset(result["selected"])

def test_unknown_config_falls_back_to_full():
    result = select(["config/rules.json"], mode="fast")
    assert result["full_suite"]

def test_docs_skip():
    result = select(["README.md"], mode="safe")
    assert result["selected"] == []

def test_empty_diff_runs_full():
    assert select([], mode="fast")["full_suite"]

def test_ai_response_allowlist(monkeypatch):
    import io
    import json
    from tools import ai_advisor

    class Response(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *args): self.close()

    payload = {"response": json.dumps({"tests": ["tests/test_checkout.py", "../../private.py", "tests/test_checkout.py"]})}
    monkeypatch.setattr(ai_advisor, "urlopen", lambda req, timeout: Response(json.dumps(payload).encode()))
    assert ai_advisor.advise(["shop/risk.py"], ["tests/test_checkout.py"], "local-test-model") == ["tests/test_checkout.py"]
