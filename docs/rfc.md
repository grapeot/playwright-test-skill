# Playwright Test Skill — RFC

## Architecture

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

## CDP Connection

Each CLI invocation:
1. Connects to `http://localhost:9222` via `playwright.chromium.connect_over_cdp()`
2. Gets the first existing browser context (or creates one)
3. Gets the first existing page (or creates one)
4. Executes the command
5. Prints output to stdout
6. Returns exit code 0 on success, 1 on error

The browser is not closed by the CLI — it persists across invocations. The agent starts it once with `--remote-debugging-port` and closes it manually when done.

## Command Specifications

### `goto <url>`
- Navigate to URL with `wait_until="domcontentloaded"` (not `networkidle` — SPA pages may never reach idle)
- Timeout: 30s
- Output: `URL: <url>` and `Title: <title>`

### `click <selector>`
- Wait for element to be visible (10s timeout)
- Click with 5s timeout
- Uses Playwright's `locator()` API for CSS + text selectors
- Output: `Clicked: <selector>` or error message

### `fill <selector> <value>`
- Wait for element to be visible (10s timeout)
- Fill with 5s timeout
- Output: `Filled: <selector> = <value>` or error message

### `snapshot`
The core command. Prints:
- URL and title
- Body text (first 2000 chars)
- All `<input>` elements: name, type, placeholder, visible, value
- All `<button>` and `<a role="button">` elements: text, visible, disabled
- First 10 `<a>` links: text, href, visible
- Modal content (if `div.ReactModalPortal` exists)
- Format is plain text with section headers, parseable by agents

### `wait <ms>`
- `page.wait_for_timeout(ms)`
- Output: `Waited <ms>ms`

### `reload`
- Reload with `wait_until="domcontentloaded"`
- Output: `Reloaded. URL: <url>`

### `eval <js_expression>`
- Evaluate JS in page context
- Output: `Result: <result>`

### `url` / `title`
- Print just the URL or title

### `screenshot <path>`
- Full-page screenshot
- Output: `Screenshot saved: <path>`

### `storage`
- Print all cookies and localStorage entries
- Useful for debugging SSO session state

## Dependencies

- `playwright` (Python package, requires `python -m playwright install chromium`)
- Python 3.10+

## Environment

- No `.env` needed — CDP URL is hardcoded to `http://localhost:9222` (configurable via `PW_TEST_CDP_URL` env var)
- No API keys, no credentials, no sensitive data

## Error Handling

- CDP connection failure: clear error message with instructions to start Chrome
- Element not found: print timeout error, don't crash
- JS eval failure: print exception message
- All errors go to stderr, results go to stdout