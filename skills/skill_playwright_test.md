# Playwright E2E Test Skill

## Metadata

- **Type**: Workflow
- **Applicable scenarios**: Writing or debugging E2E tests for web applications, especially with third-party SSO, multi-step registration, dynamic modals, or any flow where page behavior is unpredictable
- **Created**: 2026-06-29

## Goal

Write reliable Playwright E2E tests by first exploring the target application's page structure and interaction flow through incremental CDP debugging, then automating the discovered flow.

## Why this skill exists

E2E test writing is an exploration problem, not a coding problem. You can't write reliable automation for a flow you haven't observed. When an agent writes a full Playwright script upfront — without knowing what modals will appear, what selectors will resolve, what redirects will happen — it ends up in a guess-and-retry loop that burns tokens without converging.

This skill prescribes a manual-first methodology: explore the page step by step using CDP, observe what actually happens at each interaction, then write automation that reproduces the observed flow. The CLI (`pw-test`) provides the step-by-step primitives that make this practical from a terminal.

## Acceptance Criteria

1. An agent reading this skill file can follow the manual-first methodology without additional guidance
2. The agent uses `snapshot` (text DOM state) as the primary observation tool, not screenshots
3. After exploration, the agent writes a Playwright test script that reproduces the discovered steps with `wait_for` selectors instead of fixed timeouts
4. The agent cleans up the CDP Chrome profile after the session to avoid stale session tokens in future runs

## Methodology

1. **Start CDP Chrome** with a fresh user-data-dir (clean profile avoids stale SSO session tokens)
2. **Navigate** to the target page with `pw-test goto`
3. **Snapshot** with `pw-test snapshot` to see the full DOM state — this is the primary tool
4. **Interact** with `pw-test click`/`fill` based on what the snapshot revealed
5. **Snapshot again** after each interaction to observe what changed
6. **Repeat** until the full flow is understood
7. **Write the Playwright test** that reproduces the discovered steps with `wait_for` selectors instead of fixed timeouts
8. **Clean up**: kill Chrome, remove the user-data-dir

## Available Resources

- **CLI**: `pw-test` (installed via `pip install -e .` from [grapeot/playwright-test-skill](https://github.com/grapeot/playwright-test-skill))
- **CDP Chrome**: agent starts Chrome with `--remote-debugging-port=9222 --user-data-dir=/tmp/pw_debug_profile`
- **Playwright**: required Python package, Chromium browser must be installed (`python -m playwright install chromium`)
- **Env var**: `PW_TEST_CDP_URL` (default `http://localhost:9222`)

### CLI Commands

| Command | Args | Description |
|---------|------|-------------|
| `goto` | `<url>` | Navigate to URL (waits for DOM content loaded) |
| `click` | `<selector>` | Click an element (Playwright selector syntax) |
| `fill` | `<selector> <value>` | Fill an input field |
| `snapshot` | — | Print full page state: URL, title, body text, all inputs, buttons, links, modals |
| `wait` | `<ms>` | Wait for duration in milliseconds |
| `reload` | — | Reload the page |
| `eval` | `<js>` | Evaluate JavaScript in page context |
| `url` | — | Print current URL |
| `title` | — | Print page title |
| `screenshot` | `<path>` | Save full-page screenshot |
| `storage` | — | Print cookies and localStorage |

## Known Pitfalls

### 1. Stale CDP Chrome profile causes SSO SDK infinite redirect loops

**Symptom:** Page oscillates between "loading" and "signing in" states; backend logs show repeated 401s.

**Cause:** The CDP Chrome user-data-dir contains session tokens from a previous test. The SSO SDK detects the old token, uses it, gets 401, refreshes, gets 401 again — infinite loop.

**Fix:** Always start with a fresh user-data-dir: `rm -rf /tmp/pw_debug_profile` before starting Chrome. In automation, use `browser.new_context()` to avoid inheriting sessions.

### 2. `networkidle` wait causes timeouts on SPAs

**Symptom:** `goto` hangs for 30s then times out on pages with persistent connections (WebSocket, polling, analytics).

**Cause:** SPA pages may never reach `networkidle` because of background requests.

**Fix:** Use `wait_until="domcontentloaded"` instead of `networkidle`. The CLI already does this.

### 3. Modal buttons not found via `querySelectorAll`

**Symptom:** `eval` returns empty array when trying to find buttons inside a React Modal Portal, but `snapshot` shows the buttons.

**Cause:** React Modal Portal may use shadow DOM or the modal content is rendered in a way that `document.querySelector` doesn't traverse.

**Fix:** Use `pw-test click "div.ReactModalPortal button:has-text('Continue')"` (Playwright locator) instead of `eval` with `querySelector`.

### 4. Logto register flow doesn't set `lastSignInAt`

**Symptom:** After guest registers via signup URL (verification code → set password → profile), Logto Management API returns `lastSignInAt=null`.

**Cause:** Register creates the user and sets a password, but doesn't constitute a sign-in. `lastSignInAt` only updates on actual sign-in.

**Fix:** `has_logged_in=0` after register is expected behavior. To verify `has_logged_in=1`, the guest must complete a real sign-in (not register).

## Relationship to other skills

- `bestpractice_gui_automation.md` — general GUI automation methodology
- `bestpractice_staged_approach.md` — staged approach; E2E debugging naturally fits "isolate then automate"