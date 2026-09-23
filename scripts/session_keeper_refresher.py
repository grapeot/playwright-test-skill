"""Session keeper — reference implementation.

Maintains credentials for a web app that issues browser-bound session tokens
(JWT + session headers) with no programmatic refresh endpoint. The browser
profile holds a living login; this tool captures fresh tokens from real
network traffic, verifies them against a read-only endpoint, and updates a
local `.env` file used by background automation.

Design rules enforced here (see ../skills/skill_session_keeper.md):
  - verify before write: only a live HTTP 200 authorizes `--apply`
  - credentials appear masked in all output; full values live only in the target file
  - idempotent: identical values yield `no_change` without rewriting
  - timestamped backup before every mutation
  - distinct machine-readable failure outcomes: no_cdp / no_captured_headers / verification_failed
  - read-only capture: navigation plus passive header listening, never UI mutation

Site-specific configuration (SITE block below) is intentionally inlined for
clarity. Copy this file, adapt the SITE block and the env field names for a
new site, and re-verify the capture/verify paths against that site's traffic.
Do not build a generic multi-site engine on top of this; deep customization
per site is the expected workflow.

Usage:
  session_keeper_refresher.py login
  session_keeper_refresher.py status --env-target ../.env
  session_keeper_refresher.py capture --env-target ../.env [--apply] [--wait 40]

Exit codes: 0 success; 2 expected failure (JSON `status` + `hint`); 1 usage error.
"""
import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from playwright.async_api import async_playwright

# ---------------------------------------------------------------------------
# SITE CONFIGURATION — the only block you should edit for a new site
# ---------------------------------------------------------------------------
SITE = {
    "name": "example",
    "url": "https://app.example.com/grow",           # page that issues API calls after login
    "api_marker": "app.example.com/api/",            # substring identifying API requests
    "cdp_port": 9222,
    "profile_dir": os.path.expanduser("~/.local/share/session-keeper/example"),
    "chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    # headers to capture; keys are the .env field names
    "headers": {
        "Authorization": "authorization",   # request header name -> captured value
        "Session": "session",
        "Account": "account",
    },
    "account_fallback": "replace-with-account-id",   # used when Account header absent
    # read-only endpoint used to verify candidate credentials (HTTP 200 required)
    "verify_url": "https://app.example.com/api/metric/sample?start_date=2026-01-01&end_date=2026-01-07",
    "env_field_map": {   # captured header -> .env variable name
        "Authorization": "EXAMPLE_AUTHORIZATION",
        "Session": "EXAMPLE_SESSION",
        "Account": "EXAMPLE_ACCOUNT",
    },
}
# noise substrings: requests matching these are analytics/telemetry, not API calls
NOISE = ("segment", "sentry", "amplitude", "google-analytics", "googletagmanager",
         "intercom", "doubleclick", "hotjar", "cookieyes", "bugsnag",
         "assets-v2", "packs/", "static/", "fonts", "images")

CDP = "http://localhost:9222"


def mask(value: str) -> str:
    if not value:
        return "<empty>"
    return f"{value[:8]}...{value[-6:]}({len(value)})"


def decode_jwt(auth: str):
    """Return (exp, user_id) from a JWT, or (None, None) if not decodable."""
    try:
        payload = auth.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("exp"), data.get("user_id")
    except Exception:
        return None, None


def env_var(env_path: str, name: str, default: str = "") -> str:
    if env_path and os.path.exists(env_path):
        for line in open(env_path):
            m = re.match(rf"^{name}=(.*)$", line.strip())
            if m:
                return m.group(1).strip()
    return default


def cdp_running(port: int = 9222) -> bool:
    try:
        urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=2)
        return True
    except Exception:
        return False


async def capture_headers(site_url: str, wait_seconds: int):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        found = {}
        event = asyncio.Event()

        def on_request(req):
            if SITE["api_marker"] not in req.url:
                return
            if any(n in req.url for n in NOISE):
                return
            h = req.headers
            primary = SITE["headers"].get("Authorization")
            auth = h.get(primary) if primary else None
            if not auth:
                return
            if "Authorization" not in found:
                found["Authorization"] = auth
                found["Session"] = h.get("session") or ""
                found["Account"] = h.get("account") or ""
                event.set()

        page.on("request", on_request)
        print(f"navigating to {site_url} ...", file=sys.stderr)
        try:
            await page.goto(site_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"goto warning: {e}", file=sys.stderr)
        deadline = time.time() + wait_seconds
        while time.time() < deadline and not event.is_set():
            await asyncio.sleep(1)
        if not found:  # one reload retry; SPA lazy loading can defer API calls
            try:
                await page.reload(wait_until="domcontentloaded")
            except Exception:
                pass
            deadline = time.time() + wait_seconds
            while time.time() < deadline and not event.is_set():
                await asyncio.sleep(1)
        await browser.close()
    return found


def verify(auth: str, session: str, account: str, timeout: int = 20):
    """Probe the read-only endpoint with candidate values. Returns (ok, status)."""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Referer": SITE["url"],
        "Session": session,
        "Account": account,
        "Authorization": auth,
        "Cache-Control": "no-cache",
    }
    req = urllib.request.Request(SITE["verify_url"], headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return resp.status == 200, str(resp.status)
    except urllib.error.HTTPError as e:
        return False, str(e.code)
    except Exception as e:
        return False, f"error:{e}"


def update_env(env_path: str, values: dict):
    """Write captured values into the target file after timestamped backup.

    Returns (changed_field_names, backup_path).
    """
    lines = open(env_path).read().splitlines(keepends=True)
    field_by_var = {var: field for field, var in SITE["env_field_map"].items()}
    changed = []
    seen = set()
    out = []
    for line in lines:
        m = re.match(r"^([A-Z0-9_]+)=", line)
        if m and m.group(1) in field_by_var:
            var = m.group(1)
            out.append(f"{var}={values[field_by_var[var]]}\n")
            changed.append(var)
            seen.add(var)
            continue
        out.append(line)
    for field, var in SITE["env_field_map"].items():
        if var not in seen:
            out.append(f"{var}={values[field]}\n")
            changed.append(var)
    bak = env_path + ".bak-" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(env_path, bak)
    open(env_path, "w").write("".join(out))
    return changed, bak


MODES = """Usage: session_keeper_refresher.py <login|status|capture> [args]
"""


def do_login() -> int:
    os.makedirs(SITE["profile_dir"], exist_ok=True)
    if cdp_running(SITE["cdp_port"]):
        print("CDP already running", file=sys.stderr)
    else:
        subprocess.Popen(
            [SITE["chrome"], f"--remote-debugging-port={SITE['cdp_port']}",
             f"--user-data-dir={SITE['profile_dir']}",
             "--no-first-run", "--no-default-browser-check"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(20):
            if cdp_running(SITE["cdp_port"]):
                break
            time.sleep(1)
        if not cdp_running(SITE["cdp_port"]):
            print(json.dumps({"status": "cdp_launch_failed"}))
            return 2
        print("Chrome launched with dedicated profile", file=sys.stderr)
    print("Please open the site in that Chrome window and log in.", file=sys.stderr)
    return 0


def do_status(env_target: str) -> int:
    auth = env_var(env_target, SITE["env_field_map"]["Authorization"])
    if not auth:
        print(json.dumps({"status": "missing_token", "env_target": env_target}))
        return 2
    exp, uid = decode_jwt(auth)
    if not exp:
        print(json.dumps({"status": "not_a_jwt", "auth_masked": mask(auth)}))
        return 2
    remaining_days = (datetime.fromtimestamp(exp, tz=timezone.utc) - datetime.now(timezone.utc)).days
    print(json.dumps({
        "status": "ok",
        "auth_masked": mask(auth),
        "jwt_exp_date": datetime.fromtimestamp(exp, tz=timezone.utc).isoformat(),
        "remaining_days": remaining_days,
        "user_id": uid,
    }, ensure_ascii=False))
    return 0


def do_capture(env_target: str, apply: bool, wait: int) -> int:
    if not cdp_running(SITE["cdp_port"]):
        print(json.dumps({"status": "no_cdp", "hint": "run `login` mode first"}))
        return 2
    found = asyncio.run(capture_headers(SITE["url"], wait))
    if not found.get("Authorization"):
        print(json.dumps({"status": "no_captured_headers",
                          "hint": "open/log into the site in the CDP Chrome window, then retry"}))
        return 2

    auth = found["Authorization"]
    session = found.get("Session", "")
    account = found.get("Account") or SITE["account_fallback"]
    exp, uid = decode_jwt(auth)
    ok, status = verify(auth, session, account)
    out = {
        "mode": "capture",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "auth_masked": mask(auth),
        "session_masked": mask(session),
        "account": account,
        "jwt_exp_date": datetime.fromtimestamp(exp, tz=timezone.utc).isoformat() if exp else None,
        "verify_status": status,
        "verified_ok": ok,
    }
    if not os.path.exists(env_target):
        out["env_update"] = "skipped (target file missing)"
    elif ok and apply:
        values = {"Authorization": auth, "Session": session, "Account": account}
        old = {v: env_var(env_target, v) for v in SITE["env_field_map"].values()}
        new = {v: values[f] for f, v in SITE["env_field_map"].items()}
        if old == new:
            out["env_update"] = "no_change"
        else:
            changed, bak = update_env(env_target, values)
            out["env_update"] = "applied"
            out["env_changed_fields"] = changed
            out["env_backup"] = bak
    elif ok:
        out["env_update"] = "verified_not_applied (add --apply to write)"
    else:
        out["env_update"] = "skipped (verification failed)"
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if ok else 2


def main():
    if len(sys.argv) < 2:
        print(MODES, file=sys.stderr)
        return 1
    mode = sys.argv[1]
    args = sys.argv[2:]

    if mode == "login":
        return do_login()

    def argval(flag: str):
        return args[args.index(flag) + 1] if flag in args else None

    if mode == "status":
        env_target = argval("--env-target") or ".env"
        return do_status(env_target)

    if mode == "capture":
        env_target = argval("--env-target")
        apply = "--apply" in args
        wait = int(argval("--wait") or 40)
        return do_capture(env_target, apply, wait)

    print(f"unknown mode: {mode}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())