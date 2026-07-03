# Changelog

## 2026-07-03

- Reframed the skill around when to use CDP exploration: unknown browser flows, third-party auth/callbacks, dynamic SPAs, and E2E failure triage
- Added hybrid E2E guidance: use browser automation to acquire real session/code artifacts, then use API/protocol assertions when they are more deterministic
- Added CLI commands: `diagnose`, `elements`, `wait-for-selector`, `wait-for-url`
- Fixed valid-command execution path and added a fake CDP regression test so command dispatch cannot silently return without running
- Updated README, PRD, RFC, test strategy, and skill file for the new triage/observation primitives
- Expanded unit tests for new command argument validation; latest suite: 13 passed
- Live smoke verified against headless Chromium CDP: `goto`, `wait-for-selector`, `elements`, `diagnose`

## 2026-06-29

- Project scaffolded from CDP debugging experience during Buddy Pass E2E development
- CLI implementation: goto, click, fill, snapshot, wait, reload, eval, url, title, screenshot, storage
- Unit tests for argument validation (11 tests)
- PRD, RFC, test.md, README, AGENTS.md written
- Skill file (`skill_playwright_test.md`) written following meta-skill guidelines

## Lessons Learned

- `networkidle` wait strategy causes timeouts on SPA pages — use `domcontentloaded` instead
- Each CLI invocation must be a separate process; the browser persists because it's a separate Chrome process started by the agent
- `snapshot` text output is more useful than screenshots for AI agents that can't process images
- CDP Chrome profile must be cleaned between sessions to avoid stale SSO session tokens causing infinite redirect loops
