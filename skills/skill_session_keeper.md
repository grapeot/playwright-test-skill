# Browser Session Credential Keeper Skill

## Metadata

- **Type**: Workflow
- **Applicable scenarios**: Keeping credentials fresh for a logged-in web app that uses browser-issued session tokens (JWT/session cookies) instead of OAuth refresh tokens. Covers one-time manual login into a persistent browser profile, automated capture of auth headers, verification against a read-only endpoint, and verified write-back to a local `.env` file.
- **Created**: 2026-09-23

## Goal

Establish a self-healing credential chain for web apps that issue browser-bound session tokens: the browser profile maintains an active login, while a script captures fresh tokens from real network traffic, verifies them, and updates the `.env` copy used by background automation. After setup, the agent can restore expired credentials without requiring the user to re-copy values from DevTools.

## When To Use

- A web app's internal API requires per-request auth headers (JWT, session ID, account ID) that expire every few months and lack a programmatic refresh endpoint.
- Background automation (scheduled jobs, agents) consumes those credentials from a local `.env` and starts failing with 401 errors when the snapshot becomes stale.
- The user can log in manually once, but should not be asked to inspect DevTools repeatedly.

## When NOT To Use

- The app supports standard OAuth with a refresh token — automate the refresh call instead; no browser profile is needed.
- The site provides an official API key with a long lifetime for the same data — prefer it; browser sessions should be a fallback, not a default.
- You need to *reproduce* internal API calls for research — use the Ajax Capture skill instead. This skill only maintains credentials; it does not reverse-engineer API contracts.
- The token never expires, or losing it has no impact — do not build tooling for a non-problem.

## Acceptance Criteria

The chain is working when all of the following hold:

1. `status` reports the token's remaining lifetime without network calls, by decoding the JWT `exp` (or the site's equivalent expiry field).
2. `capture` obtains auth headers from at least one API request issued by the logged-in page, without requiring any user action beyond keeping the profile logged in.
3. Captured values pass live read-only verification (HTTP 200) *before* any write.
4. On a verified write, the target file is backed up with a timestamp suffix, and fields that already match are reported as `no_change` rather than rewritten.
5. Every credential value appears only masked in all output (`prefix...suffix(length)`); full values exist only in the target file.
6. Each failure mode has a distinct, machine-readable outcome: `no_cdp`, `no_captured_headers`, or `verification_failed` — each paired with its corresponding human recovery action in the skill text below.

## CLI Contract

One binary, three verbs. All output is JSON on stdout; diagnostics go to stderr; exit code 0 means the mode's goal was reached.

```
session-keeper login   --site <name> [--port 9222] [--profile-dir <path>]
session-keeper status  --env-target <path> [--field EXAMPLE_AUTHORIZATION]
session-keeper capture --site <name> [--port 9222]
    --headers Authorization,Session,Account
    --verify-url <read-only endpoint>
    --env-target <path> [--apply] [--wait 40]
```

- `login`: Launches (or reuses) a Chrome instance over CDP with a persistent profile directory. The user logs in manually; the tool never touches the login flow itself. SSO, OTP, and 2FA are black boxes.
- `status`: Reads local files only. Decodes JWT payload fields (`exp`, `user_id` if present) without network calls.
- `capture`: Connects over CDP, navigates to the target site, listens at the protocol level (`page.on("request")`), extracts the requested headers from the first API request that carries them, verifies them, and — only with `--apply` and a passing verification — updates the target file.

**Reference implementation.** `scripts/session_keeper_refresher.py` in this repo is a complete, runnable single-site implementation with the site configuration inlined in one `SITE` block. To adapt it for a new site, copy the file, rewrite the `SITE` block (URL, API marker, header names, verify URL, env field map) and the header-extraction rule, then re-run the capture and verification paths against that site's traffic. Do not build a shared multi-site engine on top of it: deep per-site customization is the expected workflow, and the copy step is deliberate.

## Design Rules (enforcing constraints)

**Verify before write.** A captured value is a candidate, not a credential. Probe the configured read-only endpoint with the candidate values; only a 200 response authorizes `--apply`. If the site has no clean read-only endpoint, `--apply` must be refused — output the captured values for human confirmation instead. This is a hard constraint, not a suggestion.

**Mask everywhere.** Logs, stdout, and error messages show `prefix...suffix(length)`. Full values live only in the target file. Backups inherit the file's own permissions.

**Idempotent runs.** If captured values match the current target values, report `no_change` and exit 0. Scheduled re-runs and concurrent manual runs are both safe.

**Backups before every mutation.** Back up to `<target>.bak-<YYYYMMDD_HHMMSS>` before modifying the file; the skill text should point the operator at the backup path on failure.

**Distinct failure outcomes.** `no_cdp` (Chrome not running — run `login`), `no_captured_headers` (profile not logged in or page didn't issue API calls — user opens/refreshes the site in that window), and `verification_failed` (captured values are invalid — do not write; surface the HTTP status). Each outcome maps to one specific human recovery action.

**Profile placement.** Use a persistent path by default (for example `~/.local/share/session-keeper/<site>/`), never `/tmp` alone — a rebooted machine must not silently destroy the login. Profile loss is an expected, documented recovery path ("log in once more"), not a defect.

**One site per port.** Port and profile directory are keyed by site name to allow parallel keepers for different sites (9222, 9223, ...).

**Read-only capture.** The capture flow must not click, submit, or otherwise mutate state in the target web app. Navigation plus passive header listening only.

## Known Pitfalls (from real runs)

- **Tokens are re-issued per page load.** Two captures in the same session can yield different JWT values; this is normal, not a leak. Compare values against the target file to decide whether a write is needed.
- **CLI exit 0 can hide HTTP 401.** Wrappers that return exit code 0 on a graceful error body will mislead scheduled jobs; inspect the semantic status, not the process exit code.
- **The account/site identifier header may not appear on every request.** Fall back to the existing value in the target file; do not treat its absence as a capture failure.
- **Expiry dates lie if you misread the unit.** Decode `exp` as a Unix timestamp and print the absolute date; a raw epoch number is easy to misread as "years away".
- **Header capture can miss SPA lazy loading.** If nothing is captured, one reload retry is usually enough; longer wait times rarely help.
- **A stale profile looks like a script bug.** When `capture` repeatedly fails with `no_captured_headers`, the human fix is a one-time re-login in the managed window — surface this as a prompt, not an error loop.

## Relationship to Other Skills

- `playwright_e2e` / `pw-test`: Shares the CDP Chrome launch pattern and venv; that skill observes pages to build tests, while this one maintains credentials.
- `playwright_ajax_capture`: Uses the same passive interception primitive (`page.on`), but targets a different deliverable — API contract knowledge, not credential state.
- Scheduled-job integration: Prefer a scheduled task that checks token expiry first (local, cheap) and runs `capture --apply` only inside a warning window (for example, two weeks before expiry). Avoid a dedicated browser-refresh daemon; the maintenance cost usually exceeds the three minutes a human would spend per quarter.

## Output Specification

All modes emit a single JSON object:

```json
{
  "mode": "capture",
  "captured_at": "2026-09-23T17:14:37Z",
  "auth_masked": "eyJhbGci...xYz123(336)",
  "session_masked": "a1b2c3d4...f6e7d8(36)",
  "jwt_exp_date": "2026-12-22T17:14:29Z",
  "verify_status": "200",
  "verified_ok": true,
  "env_update": "applied",
  "env_changed_fields": ["EXAMPLE_AUTHORIZATION", "EXAMPLE_SESSION"],
  "env_backup": "/path/.env.bak-20260923_101437"
}
```

Exit codes: `0` for success; `2` for expected failure (with `status` and `hint` fields); `1` for usage error.
