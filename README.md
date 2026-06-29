# Playwright Test Skill

A CLI tool that lets AI agents interactively debug web applications through Chrome DevTools Protocol (CDP).

## Why

When writing E2E tests for web applications (especially with third-party SSO, multi-step registration, or dynamic modals), you don't know what the page will do next. Writing a full Playwright automation script upfront leads to repeated failures: wrong selectors, unexpected modals, missing waits. This tool lets you step through a browser session one action at a time — `goto`, `snapshot`, `click`, `fill` — observing the DOM state after each step before committing to automation.

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

### 2. Run commands

```bash
pw-test goto "http://localhost:3000"
pw-test snapshot
pw-test click "button:has-text('Sign in')"
pw-test fill "input[name='email']" "alice@example.com"
pw-test snapshot
pw-test screenshot /tmp/page.png
```

### 3. Clean up when done

```bash
pkill -f "remote-debugging-port=9222"
rm -rf /tmp/pw_debug_profile
```

## Commands

| Command | Description |
|---------|-------------|
| `goto <url>` | Navigate to URL (waits for DOM, not network idle) |
| `click <selector>` | Click an element (Playwright selector syntax) |
| `fill <selector> <value>` | Fill an input field |
| `snapshot` | Print full page state: URL, title, body text, all inputs, buttons, links, modals |
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

## How AI Agents Can Use This

1. Start CDP Chrome (see step 1 above)
2. Use `goto` to navigate to the target page
3. Use `snapshot` to see the full DOM state in text form
4. Based on the snapshot, use `click`/`fill` to interact with elements
5. Use `snapshot` again after each interaction to see what changed
6. Once the flow is understood, write a Playwright test script that reproduces the steps

The `snapshot` command is designed to be the primary tool — it gives a complete text representation of the page without needing screenshots, which many AI agents cannot process.

## Install as a Skill

To integrate this tool into an AI agent's workspace:

1. Clone this repo
2. Install: `pip install -e . && python -m playwright install chromium`
3. Point your workspace's skill discovery (e.g. `rules/skills/INDEX.md` or `AGENTS.md`) to `skills/skill_playwright_test.md` in this repo
4. The agent can now use `pw-test` commands directly from the terminal