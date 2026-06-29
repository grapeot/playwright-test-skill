# AGENTS.md — playwright-test-skill

## Project Overview

Public CLI tool for CDP step-by-step browser debugging. English working language. Public GitHub repo.

## Project Structure

```
playwright_test_skill/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .gitignore
├── docs/
│   ├── prd.md
│   ├── rfc.md
│   ├── working.md
│   └── test.md
├── src/
│   └── playwright_test_skill/
│       ├── __init__.py
│       └── cli.py
├── tests/
│   └── test_cli.py
└── skills/
    └── skill_playwright_test.md
```

## Development Rules

- Update `docs/working.md` changelog after each change
- Frequent commits, one logical change per commit
- Python: uv managed venv in project root
- Test command: `.venv/bin/python -m pytest tests/ -v`

## Public Repo Hygiene

- No real emails, phone numbers, API keys, internal paths, or 1Password references in any committed file
- Use fake handles: `alice@example.com`, `replace-with-your-key`, `example.com`
- `.gitignore` blocks `.env`, `__pycache__/`, `.pytest_cache/`, `*.pyc`, dist/build artifacts
- `.env.example` uses fake placeholder values only
- Privacy scan before every release: `rg -n "op://|internal|private key" .` must return zero matches

## Compatibility Constraints

- CDP URL defaults to `http://localhost:9222`, overridable via `PW_TEST_CDP_URL` env var
- `goto` uses `wait_until="domcontentloaded"` not `networkidle` (SPAs may never reach idle)
- Each CLI invocation is a separate process — no persistent daemon, no state between calls