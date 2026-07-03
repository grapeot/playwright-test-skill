# Playwright E2E Test Skill

## Metadata

- **Type**: Workflow
- **Applicable scenarios**: Writing or debugging E2E tests for web applications, especially with third-party SSO, multi-step registration, dynamic modals, or any flow where page behavior is unpredictable
- **Created**: 2026-06-29

## Goal

Help an AI agent turn an unknown or unstable browser flow into a reliable E2E test or a defensible diagnosis by observing the live page step by step before writing automation.

## When to Use This Skill

Use this skill when the browser flow is not already well understood:

- Third-party SSO, OTP, OAuth callbacks, payment, or other multi-domain flows
- Dynamic SPAs where selectors, modals, redirects, or async rendering are uncertain
- E2E failures where the agent needs to determine whether the problem is product behavior, test environment, auth configuration, stale browser state, or bad test data
- Bugfix work where the agent should first reproduce the visible failure, then automate the regression check

Do not use this skill for simple, deterministic component tests or API-only behavior. If a normal Playwright test can be written from the code alone, the CDP exploration loop is unnecessary overhead.

## Why this skill exists

E2E test writing is an exploration problem, not a coding problem. You can't write reliable automation for a flow you haven't observed. When an agent writes a full Playwright script upfront — without knowing what modals will appear, what selectors will resolve, what redirects will happen — it ends up in a guess-and-retry loop that burns tokens without converging.

This skill prescribes a manual-first methodology: explore the page step by step using CDP, observe what actually happens at each interaction, then write automation that reproduces the observed flow. The CLI (`pw-test`) provides the observation and interaction primitives that make this practical from a terminal.

The core judgment is not "drive everything through the UI." For complex SSO or callback flows, a hybrid test is often more reliable: use the browser for the part that genuinely requires a browser session, then use protocol/API calls for deterministic assertions.

## Acceptance Criteria

1. An agent reading this skill file can follow the manual-first methodology without additional guidance
2. The agent uses `snapshot` (text DOM state) as the primary observation tool, not screenshots
3. When a selector or expected page state is missing, the agent captures diagnostics (`diagnose`, URL, body text, controls, optional screenshot) before changing code or adding timeouts
4. Bugfix-oriented E2E work first demonstrates the old behavior failing, then verifies the fixed behavior passing
5. After exploration, the agent writes a Playwright test script that reproduces the discovered steps with condition-based waits instead of fixed timeouts
6. The agent cleans up the CDP Chrome profile after the session to avoid stale session tokens in future runs

## Methodology

1. **Start CDP Chrome** with a fresh user-data-dir (clean profile avoids stale SSO session tokens)
2. **Navigate** to the target page with `pw-test goto`
3. **Snapshot** with `pw-test snapshot` to see the full DOM state — this is the primary tool
4. **Interact** with `pw-test click`/`fill` based on what the snapshot revealed
5. **Wait on conditions**, not time: use `wait-for-selector` or `wait-for-url` when the next state is known
6. **Diagnose before retrying**: if the expected selector or URL does not appear, run `pw-test diagnose` before adding sleeps or changing product code
7. **Repeat** until the full flow is understood
8. **Write the Playwright test** that reproduces the discovered steps with condition-based waits instead of fixed timeouts
9. **Clean up**: kill Chrome, remove the user-data-dir

## Hybrid E2E Pattern

For third-party auth and callback flows, the reliable boundary is often smaller than the whole UI journey. A good test can use Playwright to perform browser-only work (entering credentials, solving an OTP flow, accepting a consent screen, capturing an authorization code), then switch to protocol/API calls to verify the product behavior deterministically.

This is still E2E if it validates the real integration boundary. The browser is a tool for acquiring realistic session state; it does not have to be the mechanism for every assertion.

Use this pattern when full UI automation is dominated by third-party redirects, timing, or provider UI changes, while the product assertion can be made more reliably through HTTP/API.

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
| `diagnose` | `[screenshot_path]` | Print URL/title/referrer/body/controls and optionally save a screenshot |
| `elements` | `<selector>` | Print count, text, visibility, enabled state, and bounding boxes for matching elements |
| `wait-for-selector` | `<selector> [state] [timeout_ms]` | Wait for selector state (`visible` by default) |
| `wait-for-url` | `<pattern> [timeout_ms]` | Wait for the current URL to match a Playwright URL pattern |
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

### 5. Selector missing does not imply product bug

**Symptom:** A locator times out, and the agent starts changing selectors or product code blindly.

**Cause:** The browser may be on an auth provider error page, a wrong redirect URI, a stale session state, or a different environment than expected.

**Fix:** Run `pw-test diagnose` before retrying. First classify the failure: product behavior, test environment, third-party auth configuration, browser session state, or test data state.

### 6. Full UI automation is not always the most reliable E2E boundary

**Symptom:** The agent spends most of the time fighting third-party redirects, callback timing, or provider UI changes, while the product assertion is simple.

**Cause:** The test is trying to drive every step through the UI even when only part of the flow requires a browser.

**Fix:** Use the hybrid E2E pattern. Let Playwright acquire the realistic browser/session artifact, then verify product behavior through API/protocol calls when that gives a more deterministic assertion.

## Relationship to other skills

- `bestpractice_gui_automation.md` — general GUI automation methodology
- `bestpractice_staged_approach.md` — staged approach; E2E debugging naturally fits "isolate then automate"
