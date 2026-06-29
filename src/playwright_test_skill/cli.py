"""Playwright Test Skill — CDP step-by-step debugging CLI."""
from __future__ import annotations

import os
import sys
from typing import Any

CDP_URL = os.environ.get("PW_TEST_CDP_URL", "http://localhost:9222")

USAGE = """\
Usage: pw-test <command> [args...]

Commands:
  goto <url>              Navigate to URL
  click <selector>        Click an element
  fill <selector> <val>  Fill an input
  snapshot                Print full page state (URL, text, inputs, buttons, links, modals)
  wait <ms>              Wait for duration
  reload                 Reload the page
  eval <js>              Evaluate JavaScript and print result
  url                    Print current URL
  title                  Print page title
  screenshot <path>      Save full-page screenshot
  storage                Print cookies and localStorage

Environment:
  PW_TEST_CDP_URL         CDP endpoint (default: http://localhost:9222)

Setup:
  1. Start Chrome with CDP:
     <chromium> --remote-debugging-port=9222 --disable-extensions \\
       --user-data-dir=/tmp/pw_debug_profile about:blank
  2. Run pw-test commands to step through the browser session.
"""


async def _get_page(browser):
    """Get existing context/page or create one."""
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = context.pages[0] if context.pages else await context.new_page()
    return page


async def _snapshot(page) -> str:
    """Print full page state as text."""
    lines = []
    lines.append("=== SNAPSHOT ===")
    lines.append(f"URL: {page.url}")
    lines.append(f"Title: {await page.title()}")

    body_text = await page.locator("body").inner_text()
    lines.append(f"Body text (first 2000):\n{body_text[:2000]}")

    lines.append("\n--- Inputs ---")
    inputs = await page.locator("input").all()
    for i, inp in enumerate(inputs):
        name = await inp.get_attribute("name") or ""
        type_ = await inp.get_attribute("type") or ""
        placeholder = await inp.get_attribute("placeholder") or ""
        visible = await inp.is_visible()
        try:
            value = await inp.input_value()
        except Exception:
            value = ""
        lines.append(f"  input[{i}] name={name} type={type_} placeholder={placeholder} visible={visible} value={value}")

    lines.append("\n--- Buttons ---")
    buttons = await page.locator("button, a[role='button']").all()
    for i, btn in enumerate(buttons):
        try:
            text = (await btn.inner_text()).strip()[:80]
        except Exception:
            text = ""
        visible = await btn.is_visible()
        disabled = await btn.get_attribute("disabled")
        lines.append(f"  btn[{i}] text={text!r} visible={visible} disabled={disabled}")

    lines.append("\n--- Links ---")
    links = await page.locator("a").all()
    for i, link in enumerate(links[:10]):
        try:
            text = (await link.inner_text()).strip()[:60]
        except Exception:
            text = ""
        href = await link.get_attribute("href") or ""
        visible = await link.is_visible()
        lines.append(f"  link[{i}] text={text!r} href={href[:80]} visible={visible}")

    # Check for modals (React Modal Portal and generic modal patterns)
    for modal_selector in ["div.ReactModalPortal", "[role='dialog']", ".modal"]:
        modal = page.locator(modal_selector).first
        if await modal.count():
            try:
                modal_text = await modal.inner_text()
                lines.append(f"\n--- Modal ({modal_selector}) ---\n{modal_text[:500]}")
            except Exception:
                lines.append(f"\n--- Modal ({modal_selector}) present but unreadable ---")

    lines.append("=== END SNAPSHOT ===")
    return "\n".join(lines)


async def _storage(context, page) -> str:
    """Print cookies and localStorage."""
    lines = []
    cookies = await context.cookies()
    lines.append(f"Cookies ({len(cookies)}):")
    for c in cookies:
        lines.append(f"  {c.get('name')}={c.get('value')[:50]} domain={c.get('domain')}")
    try:
        local_storage = await page.evaluate("() => Object.entries(localStorage)")
        lines.append(f"\nLocalStorage ({len(local_storage)} entries):")
        for key, val in local_storage:
            lines.append(f"  {key}={str(val)[:100]}")
    except Exception:
        lines.append("\nLocalStorage: unavailable")
    return "\n".join(lines)


async def async_main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    if not argv:
        print(USAGE, file=sys.stderr)
        return 1

    cmd = argv[0]
    args = argv[1:]

    # Pre-CDP argument validation (fail fast before connecting)
    if cmd == "goto" and not args:
        print("Error: goto requires a URL argument", file=sys.stderr)
        return 1
    if cmd == "click" and not args:
        print("Error: click requires a selector argument", file=sys.stderr)
        return 1
    if cmd == "fill" and len(args) < 2:
        print("Error: fill requires <selector> and <value> arguments", file=sys.stderr)
        return 1
    if cmd == "wait" and not args:
        print("Error: wait requires a duration in ms", file=sys.stderr)
        return 1
    if cmd == "eval" and not args:
        print("Error: eval requires a JavaScript expression", file=sys.stderr)
        return 1
    if cmd == "screenshot" and not args:
        print("Error: screenshot requires a file path", file=sys.stderr)
        return 1

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Error: playwright not installed. Run: pip install playwright && python -m playwright install chromium", file=sys.stderr)
        return 1

    import asyncio

    async def _run() -> int:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.connect_over_cdp(CDP_URL)
            except Exception as exc:
                print(f"Error: Cannot connect to CDP at {CDP_URL}. Start Chrome with --remote-debugging-port=9222 first.\n{exc}", file=sys.stderr)
                return 1

            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()

            if cmd == "goto":
                await page.goto(args[0], wait_until="domcontentloaded", timeout=30000)
                print(f"URL: {page.url}")
                print(f"Title: {await page.title()}")

            elif cmd == "click":
                loc = page.locator(args[0]).first
                try:
                    await loc.wait_for(state="visible", timeout=10000)
                    await loc.click(timeout=5000)
                    print(f"Clicked: {args[0]}")
                except Exception as exc:
                    print(f"Click failed: {exc}", file=sys.stderr)
                    return 1

            elif cmd == "fill":
                loc = page.locator(args[0]).first
                try:
                    await loc.wait_for(state="visible", timeout=10000)
                    await loc.fill(args[1], timeout=5000)
                    print(f"Filled: {args[0]} = {args[1]}")
                except Exception as exc:
                    print(f"Fill failed: {exc}", file=sys.stderr)
                    return 1

            elif cmd == "snapshot":
                print(await _snapshot(page))

            elif cmd == "wait":
                ms = int(args[0])
                await page.wait_for_timeout(ms)
                print(f"Waited {ms}ms")

            elif cmd == "reload":
                await page.reload(wait_until="domcontentloaded")
                print(f"Reloaded. URL: {page.url}")

            elif cmd == "eval":
                result = await page.evaluate(args[0])
                print(f"Result: {result}")

            elif cmd == "url":
                print(page.url)

            elif cmd == "title":
                print(await page.title())

            elif cmd == "screenshot":
                await page.screenshot(path=args[0], full_page=True)
                print(f"Screenshot saved: {args[0]}")

            elif cmd == "storage":
                print(await _storage(context, page))

            else:
                print(f"Unknown command: {cmd}", file=sys.stderr)
                print(USAGE, file=sys.stderr)
                return 1

            return 0

        return await _run()


def main(argv: list[str] | None = None) -> int:
    """Synchronous entry point for CLI scripts."""
    import asyncio
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())