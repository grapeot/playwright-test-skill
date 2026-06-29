# Changelog

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