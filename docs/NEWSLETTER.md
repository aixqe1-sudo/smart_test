# I Let a Machine Decide Which Tests to Skip. Then I Hid a Bug in the Code.

*AI x QE | The Build & Break Lab*

A pull request changes one line. Your CI runs 8,000 regression tests. It takes an hour. Someone inevitably asks: **why can't we run only the tests that matter?**

Good question. But here's the less comfortable one: **how do you know which tests don't matter?**

I built a small Git-aware test selector to find out. It reads changed Python files, builds a dependency graph from imports, and picks only the related tests. There are two modes: an optimistic one and a conservative one. I added a bug on purpose and measured whether each mode could catch it.

This article includes the complete project, a GitHub Actions workflow, and an exercise you can reproduce in a few commands.

## The application

Our miniature checkout service has four pieces: cart totals, pricing, risk approval, and checkout. There are unit tests for each piece and an integration test for the end-to-end order decision.

The regression is simple: a risk rule designed to reject orders above 500 is changed so it approves every amount. An order worth 750 must be rejected, but after the injected change, it is accepted. We're not testing a real banking system. All amounts and approval rules are fictional.

## Build the selector

The key idea is a graph:

```text
Git change --> source modules --> tests importing those modules
                              --> tests importing downstream modules
```

The engine parses Python imports with `ast`, recursively walks the graph, and creates a JSON selection report. The default engine does not call an LLM. That is intentional. A cheap, explainable dependency model is our baseline. There is also an optional local Ollama advisor that may **add** tests based on source context, but it cannot remove the baseline selection. Any recommendation still needs independent verification.

The first surprise is in `shop/checkout.py`:

```python
from importlib import import_module
risk = import_module("shop.risk")
```

This runtime dependency doesn't look like an ordinary import edge in our AST graph. As a result, the `fast` selector doesn't recognize that a risk-rule change might also affect checkout integration tests.

## Run it yourself

Create a virtual environment, install `pytest`, and run the baseline:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

Then run our isolated experiment:

```bash
python -m tools.demo
```

The script copies the project into a temporary directory and injects the defective statement `return True` into the risk rule. You don't need to edit files or reset your repo afterward.

Here's what to look for:

| Execution | Expected observation |
|---|---|
| Full suite before injection | Green |
| `fast` selection after injection | Green, but misses the checkout failure |
| `safe` selection after injection | Red; falls back to the full suite |
| Independently run full suite | Red; proves the missed defect |

The `fast` outcome is not success. It's a **dangerous green**. We reduced test execution, but lost the evidence we needed to catch the change.

## Why the safeguard matters

A static test-impact map is a useful optimization. It's not a complete model of the application. Runtime imports, configuration, data dependencies, external services, feature flags, and transitive contracts all produce relationships the source-code graph may not capture.

Our conservative mode sees dynamic importing in the app and runs the full suite when production code changes. That's slower, but the safety claim is more defensible. We prefer a slower pipeline to confidently merging a defect.

For production, I'd add three more gates: runtime execution traces to improve the dependency map, periodic full-suite audits to measure false negatives, and a policy that restores full testing when the selector has low confidence.

## Where is the AI?

The repo includes an optional local Ollama advisor. Run `python -m tools.selector --changed shop/risk.py --mode fast --ai` after installing Ollama and setting `OLLAMA_MODEL`. The model proposes additional impacted tests based on changed source code and the available test filenames. It can only **add** tests to the deterministic baseline. We still audit what it chooses. AI is an experimental extension, not a prerequisite for the core lab.

That distinction matters. Smarter test selection is not the same thing as fewer tests.

## Your turn

Download the full repository linked with this edition, run `python -m tools.demo`, and try improving the selector. Can you catch the hidden risk-rule defect *without* running every test? Share your selection ratio and missed-defect count. A green build is only convincing if we can explain what it actually validated.

**What I'd like to know:** Would you let an AI system decide which tests to skip in your production release pipeline? Under what evidence and safety constraints?
