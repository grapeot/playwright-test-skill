# Playwright Test Skill

A skill that teaches AI agents how to turn unknown or unstable browser flows into reliable E2E tests or defensible diagnoses through manual-first CDP exploration, backed by a CLI for step-by-step browser observation and interaction.

## What this is

This is a **skill** for AI coding agents — a reusable capability definition that prescribes a methodology for writing reliable E2E tests. The skill is backed by a CLI tool (`pw-test`) that provides step-by-step browser interaction primitives, enabling the agent to explore a live page before committing to automation.

The core insight: E2E test writing is often an exploration problem, not just a coding problem. You can't write reliable automation for a flow you haven't observed. The skill teaches agents to explore first (using the CLI to step through a real browser session), then automate or diagnose from observed reality.

Use it for third-party SSO, OTP, OAuth callbacks, dynamic SPAs, unpredictable modals, and failing E2E tests where the agent first needs to classify whether the failure is product behavior, environment/config, browser state, or test data. Skip it for simple deterministic tests that can be written directly from the code.

## Install

```bash
pip install -e .
python -m playwright install chromium
```

## Usage

### 1. Start Chrome with CDP

```bash
"<chromium_path>" --remote-debugging-port=9222 --disable-extensions \
  --user-data-dir=/tmp/pw_debug_profile about:blank &
```

On macOS, the Chromium path is typically:
`~/Library/Caches/ms-playwright/chromium-XXXX/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`

### 2. Follow the skill methodology

```bash
pw-test goto "http://localhost:3000"
pw-test snapshot
pw-test click "button:has-text('Sign in')"
pw-test wait-for-url "**/sign-in**"
pw-test fill "input[name='email']" "alice@example.com"
pw-test snapshot
pw-test diagnose /tmp/login-debug.png
pw-test screenshot /tmp/page.png
```

### 3. Clean up when done

```bash
pkill -f "remote-debugging-port=9222"
rm -rf /tmp/pw_debug_profile
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `goto <url>` | Navigate to URL (waits for DOM, not network idle) |
| `click <selector>` | Click an element (Playwright selector syntax) |
| `fill <selector> <value>` | Fill an input field |
| `snapshot` | Print full page state: URL, title, body text, all inputs, buttons, links, modals |
| `diagnose [screenshot_path]` | Print URL/title/referrer/body/controls and optionally save screenshot |
| `elements <selector>` | Print count, text, visibility, enabled state, and bounding boxes |
| `wait-for-selector <selector> [state] [timeout_ms]` | Wait for selector state (`visible` by default) |
| `wait-for-url <pattern> [timeout_ms]` | Wait for URL to match a Playwright URL pattern |
| `wait <ms>` | Wait for a duration in milliseconds |
| `reload` | Reload the page |
| `eval <js>` | Evaluate JavaScript in page context |
| `url` | Print current URL |
| `title` | Print page title |
| `screenshot <path>` | Save full-page screenshot |
| `storage` | Print cookies and localStorage |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PW_TEST_CDP_URL` | `http://localhost:9222` | CDP endpoint URL |

## Install as a Skill

To integrate this skill into an AI agent's workspace:

1. Clone this repo
2. Install: `pip install -e . && python -m playwright install chromium`
3. Point your workspace's skill discovery (e.g. `rules/skills/INDEX.md` or `AGENTS.md`) to `skills/skill_playwright_test.md` in this repo
4. The agent can now follow the skill methodology and use `pw-test` commands from the terminal
