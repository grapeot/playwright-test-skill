# Playwright Test Skill — PRD

## Bottom Line

A skill that teaches AI agents how to turn unknown or unstable browser flows into reliable E2E tests or defensible diagnoses through a manual-first CDP approach: explore the page step by step, observe what actually happens at each interaction, then write automation or switch to a more deterministic protocol/API assertion. The skill is backed by a CLI (`pw-test`) that provides observation and interaction primitives — goto, snapshot, diagnose, wait-for-selector, wait-for-url, click, fill — so the agent can interact with a live browser from the terminal without writing a full script upfront.

## Problem

When writing E2E tests for web applications (especially with third-party SSO, multi-step registration, or dynamic modals), the agent doesn't know what the page will do next. Writing a full Playwright automation script upfront leads to repeated failures: wrong selectors, unexpected modals, missing waits, changed flows. The agent guesses and retries in a tight loop, burning tokens without making real progress.

The root cause is that E2E test writing is often an exploration problem, not a coding problem. You can't write reliable automation for a flow you haven't observed. The skill addresses this by prescribing a manual-first methodology — explore first, automate or diagnose second — and providing the CLI tooling that makes incremental exploration practical from a terminal.

The skill is most useful when a browser flow crosses unstable boundaries: SSO providers, OTP, OAuth callbacks, payment, dynamic modals, SPA async rendering, or failures where the agent must classify whether the issue is product behavior, test environment, third-party auth configuration, stale browser state, or test data state.

## Skill vs Tool

This project is fundamentally a **skill** (a reusable capability definition for AI agents), not a CLI tool. The skill file (`skills/skill_playwright_test.md`) is the primary artifact — it defines the goal, acceptance criteria, methodology, known pitfalls, and available resources. The CLI (`pw-test`) is an enabling resource that supports the skill's methodology. The PRD, RFC, tests, and README all serve the skill, not the other way around.

## Target Users

AI coding agents (Claude Code, Cursor, OpenCode, Codex, etc.) that need to:
1. Debug E2E test failures by stepping through a browser session
2. Explore a web application's DOM structure before writing automation
3. Understand SSO login flows that have multiple modals and redirects
4. Verify that UI changes render correctly by inspecting the live DOM
5. Capture diagnostics before changing code when selectors, redirects, or expected page states do not appear

## Skill Methodology

The skill prescribes a manual-first approach:

1. **Start CDP Chrome** with a fresh user-data-dir
2. **Navigate** to the target page
3. **Snapshot** to see the full DOM state in text form
4. **Interact** (click, fill) based on what the snapshot revealed
5. **Wait on conditions** (`wait-for-selector`, `wait-for-url`) instead of fixed sleeps when the expected next state is known
6. **Diagnose before retrying** when the expected state is missing
7. **Repeat** until the full flow is understood
8. **Write the Playwright test** that reproduces the discovered steps with condition-based waits instead of fixed timeouts, or use a hybrid browser/API test when that gives a better assertion boundary

The CLI provides the primitives for steps 1-6. Step 7 is the agent's normal coding work, now grounded in observed reality rather than guesses.

## CLI Commands (supporting the skill)

- `goto <url>` — Navigate to a URL, wait for DOM to load
- `click <selector>` — Click an element by CSS/Playwright selector
- `fill <selector> <value>` — Fill an input with a value
- `snapshot` — Print full page state: URL, title, body text, all inputs, all buttons, all links, modal content
- `diagnose [screenshot_path]` — Print a compact debug bundle; optionally save a full-page screenshot
- `elements <selector>` — Print count/text/visibility/enabled state/bounding boxes for matches
- `wait-for-selector <selector> [state] [timeout_ms]` — Wait for selector state (`visible` by default)
- `wait-for-url <pattern> [timeout_ms]` — Wait for current URL to match a Playwright URL pattern
- `wait <ms>` — Wait for a duration
- `reload` — Reload the page
- `eval <js>` — Evaluate JavaScript and print the result
- `url` — Print current URL
- `title` — Print page title
- `screenshot <path>` — Save a full-page screenshot
- `storage` — Print cookies and localStorage

## Key Design Decisions

1. **Skill is primary, CLI is supporting**: The skill file defines what the agent should do and why. The CLI provides the "how" at the execution level. An agent could follow the skill methodology without the CLI (using raw Playwright scripts), but the CLI makes it significantly more practical.

2. **Snapshot is the core primitive**: Instead of screenshots (which agents can't always process), `snapshot` prints a text representation of the DOM. This gives the agent a complete picture of the page state in text form, parseable without vision capabilities.

3. **CDP connection, not headless launch**: The agent starts Chrome separately with `--remote-debugging-port=9222`, then the CLI connects via CDP. The browser persists between CLI invocations — the agent can run `goto`, then `snapshot`, then `click` as separate commands.

4. **Known pitfalls are first-class content**: The skill documents real failures encountered during E2E development (stale SSO sessions, `networkidle` timeouts, modal button detection, Logto register vs sign-in). These are more valuable than methodology advice because the agent can't discover them on its own.

## Success Criteria

1. An AI agent reading the skill file can follow the manual-first methodology without additional guidance
2. `snapshot` output is sufficient for an agent to identify the next action without needing screenshots
3. The CLI works with any Chrome/Chromium instance that has CDP enabled
4. Known pitfalls cover real failure modes encountered in practice, not predicted hypotheticals
5. Tests cover CLI argument validation and command routing
6. The skill explains when to use CDP exploration and when to avoid it for deterministic tests
7. The skill documents the hybrid E2E pattern for third-party auth/callback flows

## Non-Goals

- Not a test runner — the skill teaches exploration methodology, not test execution
- Not a screenshot tool — text-based DOM snapshots are the primary output
- Not a browser launcher — the agent starts Chrome separately; the CLI only connects
- Not a network proxy or request interceptor
