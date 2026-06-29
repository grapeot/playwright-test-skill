# Playwright Test Skill — RFC

## Architecture

This project is a **skill** (reusable AI agent capability definition) backed by a CLI tool. The skill file is the primary artifact; the CLI is an enabling resource.

```text
Skill file (skill_playwright_test.md)
  └── defines: goal, methodology, acceptance criteria, known pitfalls
  └── references: CLI as available resource

CLI (pw-test)
  └── connects to Chrome via CDP
  └── one command per invocation, browser persists
  └── text-based snapshot output for agent consumption

Agent workflow:
  1. Reads skill file → understands manual-first methodology
  2. Starts CDP Chrome
  3. Uses pw-test commands to explore page step by step
  4. Writes Playwright test reproducing observed flow
  5. Cleans up
```

## Skill File Structure

The skill file (`skills/skill_playwright_test.md`) follows the meta-skill guidelines:
- **Goal**: one-sentence definition of what the skill accomplishes
- **Why**: the problem this skill solves (exploration before automation)
- **Acceptance criteria**: testable success conditions
- **Methodology**: manual-first CDP debugging approach (explore → observe → automate)
- **Available resources**: CLI commands, CDP Chrome setup, Playwright dependency
- **Known pitfalls**: real failures encountered during E2E development

## CLI Architecture

```text
AI Agent (terminal)
  └── pw-test <command> [args...]
        └── playwright.chromium.connect_over_cdp("http://localhost:9222")
              └── gets existing context/page (or creates one)
              └── executes single command
              └── prints result to stdout
              └── disconnects (browser stays alive)

Chrome (separate process, started by agent)
  --remote-debugging-port=9222
  --user-data-dir=/tmp/pw_debug_profile
```

Each CLI invocation:
1. Connects to `http://localhost:9222` via `playwright.chromium.connect_over_cdp()`
2. Gets the first existing browser context (or creates one)
3. Gets the first existing page (or creates one)
4. Executes the command
5. Prints output to stdout
6. Returns exit code 0 on success, 1 on error

The browser is not closed by the CLI — it persists across invocations.

## Command Specifications

### `goto <url>`
- Navigate with `wait_until="domcontentloaded"` (not `networkidle` — SPAs may never reach idle)
- Timeout: 30s
- Output: `URL: <url>` and `Title: <title>`

### `click <selector>`
- Wait for element visible (10s), click (5s)
- Playwright selector syntax (CSS + text)
- Output: `Clicked: <selector>` or error

### `fill <selector> <value>`
- Wait for element visible (10s), fill (5s)
- Output: `Filled: <selector> = <value>` or error

### `snapshot`
The core observation primitive. Prints:
- URL and title
- Body text (first 2000 chars)
- All `<input>` elements: name, type, placeholder, visible, value
- All `<button>` elements: text, visible, disabled
- First 10 `<a>` links: text, href, visible
- Modal content (ReactModalPortal, `[role="dialog"]`, `.modal`)
- Plain text format, parseable by agents without vision

### `wait <ms>` / `reload` / `eval <js>` / `url` / `title` / `screenshot <path>` / `storage`
Standard utilities. See CLI `--help` for details.

## Dependencies

- `playwright` (Python package, requires `python -m playwright install chromium`)
- Python 3.10+

## Environment

- No `.env` needed — CDP URL is `http://localhost:9222` (configurable via `PW_TEST_CDP_URL`)
- No API keys, no credentials, no sensitive data

## Error Handling

- CDP connection failure: clear error with instructions to start Chrome
- Element not found: print timeout error, don't crash
- JS eval failure: print exception message
- All errors go to stderr, results go to stdout