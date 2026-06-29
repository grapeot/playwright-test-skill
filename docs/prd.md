# Playwright Test Skill — PRD

## Bottom Line

A CLI tool that lets AI agents interactively debug web applications through Chrome DevTools Protocol (CDP). Instead of writing full Playwright automation scripts and running them blindly, an agent can step through a browser session one action at a time — goto, click, fill, snapshot — observing the DOM state after each step. This bridges the gap between "writing a test" and "understanding what the page actually does."

## Problem

When writing E2E tests for web applications (especially those with third-party SSO, multi-step registration flows, or dynamic modals), the agent doesn't know what the page will do next. Writing a full automation script upfront leads to repeated failures: wrong selectors, unexpected modals, missing waits, changed flows. The agent ends up guessing and retrying in a tight loop, burning tokens without making real progress.

## Target Users

AI coding agents (Claude Code, Cursor, OpenCode, Codex, etc.) that need to:
1. Debug E2E test failures by stepping through a browser session
2. Explore a web application's DOM structure before writing automation
3. Understand SSO login flows that have multiple modals and redirects
4. Verify that UI changes render correctly by inspecting the live DOM

## Features

### Core CLI Commands

- `goto <url>` — Navigate to a URL, wait for DOM to load
- `click <selector>` — Click an element by CSS/Playwright selector
- `fill <selector> <value>` — Fill an input with a value
- `snapshot` — Print full page state: URL, title, body text, all inputs, all buttons, all links, modal content
- `wait <ms>` — Wait for a duration
- `reload` — Reload the page
- `eval <js>` — Evaluate JavaScript and print the result
- `url` — Print current URL
- `title` — Print page title
- `screenshot <path>` — Save a full-page screenshot
- `storage` — Print cookies and localStorage

### Key Design Decisions

1. **CDP connection, not headless launch**: The agent starts a Chrome instance with `--remote-debugging-port=9222`, then the CLI connects to it via CDP. This means the browser stays alive between CLI invocations — the agent can run `goto`, then `snapshot`, then `click` as separate commands, each connecting and disconnecting.

2. **Snapshot is the core command**: Instead of screenshots (which agents can't always process), `snapshot` prints a text representation of the DOM: URL, title, body text (first 2000 chars), all inputs with attributes, all buttons with text, all links, and modal content. This gives the agent a complete picture of the page state in text form.

3. **Single-file CLI, no daemon**: Each command is a separate process that connects to CDP, does one thing, prints output, and exits. No persistent process to manage. The browser persists because it's a separate Chrome process.

4. **Playwright as the CDP client**: Uses `playwright.chromium.connect_over_cdp()` for robust CDP connection handling, selector evaluation, and element interaction.

## Success Criteria

1. An AI agent can start CDP Chrome, navigate through a multi-step SSO login flow, and capture the DOM state at each step using only CLI commands
2. `snapshot` output is sufficient for an agent to identify the next action without needing screenshots
3. The CLI works with any Chrome/Chromium instance that has CDP enabled
4. All commands have sensible timeouts and clear error messages
5. Tests cover all CLI commands with a mock CDP endpoint

## Non-Goals

- Not a test runner — this is a debugging/exploration tool, not a replacement for Playwright test scripts
- Not a screenshot tool — text-based DOM snapshots are the primary output
- Not a browser launcher — the agent starts Chrome separately; this tool only connects
- Not a network proxy or request interceptor