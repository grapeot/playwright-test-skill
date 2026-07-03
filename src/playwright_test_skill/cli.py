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
  diagnose [screenshot]   Print debug bundle; optionally save screenshot
  elements <selector>     Print count/text/visibility/bounding boxes for matching elements
  wait-for-selector <sel> Wait until selector reaches a state (default: visible)
  wait-for-url <pattern>  Wait until current URL matches a glob/regex pattern
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


async def _navigation_state(page) -> list[str]:
    """Return URL-oriented diagnostics that survive normal page rendering."""
    lines = []
    lines.append(f"URL: {page.url}")
    lines.append(f"Title: {await page.title()}")
    try:
        referrer = await page.evaluate("() => document.referrer")
        lines.append(f"Referrer: {referrer}")
    except Exception:
        lines.append("Referrer: unavailable")
    try:
        perf_entries = await page.evaluate(
            """() => performance.getEntriesByType('navigation').map(e => ({
                name: e.name,
                type: e.type,
                startTime: Math.round(e.startTime),
                duration: Math.round(e.duration),
            }))"""
        )
        lines.append(f"Navigation entries: {perf_entries}")
    except Exception:
        lines.append("Navigation entries: unavailable")
    return lines


async def _elements(page, selector: str) -> str:
    """Print structured details for elements matching a selector."""
    lines = [f"=== ELEMENTS {selector!r} ==="]
    locator = page.locator(selector)
    count = await locator.count()
    lines.append(f"Count: {count}")
    for i in range(min(count, 20)):
        item = locator.nth(i)
        try:
            text = (await item.inner_text(timeout=1000)).strip().replace("\n", " ")[:200]
        except Exception:
            text = ""
        try:
            visible = await item.is_visible(timeout=1000)
        except Exception:
            visible = False
        try:
            enabled = await item.is_enabled(timeout=1000)
        except Exception:
            enabled = False
        try:
            box = await item.bounding_box(timeout=1000)
        except Exception:
            box = None
        lines.append(f"[{i}] visible={visible} enabled={enabled} box={box} text={text!r}")
    if count > 20:
        lines.append(f"... {count - 20} more not shown")
    lines.append("=== END ELEMENTS ===")
    return "\n".join(lines)


async def _diagnose(page, screenshot_path: str | None = None) -> str:
    """Print a compact debug bundle for failed waits, auth redirects, and selector misses."""
    lines = ["=== DIAGNOSE ==="]
    lines.extend(await _navigation_state(page))
    try:
        body_text = await page.locator("body").inner_text(timeout=3000)
        lines.append(f"Body text (first 3000):\n{body_text[:3000]}")
    except Exception as exc:
        lines.append(f"Body text unavailable: {exc}")
    lines.append("\n--- Visible controls ---")
    for selector in ["input", "button", "a", "[role='dialog']"]:
        lines.append(await _elements(page, selector))
    try:
        console_errors = await page.evaluate("() => window.__pwTestConsoleErrors || []")
        lines.append(f"\nConsole errors captured: {console_errors}")
    except Exception:
        lines.append("\nConsole errors captured: unavailable")
    if screenshot_path:
        await page.screenshot(path=screenshot_path, full_page=True)
        lines.append(f"Screenshot saved: {screenshot_path}")
    lines.append("=== END DIAGNOSE ===")
    return "\n".join(lines)


async def _install_console_hook(page) -> None:
    """Best-effort in-page console error capture for later diagnose output."""
    try:
        await page.evaluate(
            """() => {
                if (!window.__pwTestConsoleHooked) {
                    window.__pwTestConsoleErrors = window.__pwTestConsoleErrors || [];
                    window.__pwTestConsoleHooked = true;
                    const oldError = console.error;
                    console.error = (...args) => {
                        window.__pwTestConsoleErrors.push(args.map(String).join(' '));
                        oldError.apply(console, args);
                    };
                }
            }"""
        )
    except Exception:
        return


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
    if cmd == "elements" and not args:
        print("Error: elements requires a selector argument", file=sys.stderr)
        return 1
    if cmd == "wait-for-selector" and not args:
        print("Error: wait-for-selector requires a selector argument", file=sys.stderr)
        return 1
    if cmd == "wait-for-url" and not args:
        print("Error: wait-for-url requires a URL pattern argument", file=sys.stderr)
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
            await _install_console_hook(page)

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

            elif cmd == "diagnose":
                print(await _diagnose(page, args[0] if args else None))

            elif cmd == "elements":
                print(await _elements(page, args[0]))

            elif cmd == "wait-for-selector":
                state = args[1] if len(args) > 1 else "visible"
                timeout = int(args[2]) if len(args) > 2 else 10000
                await page.locator(args[0]).first.wait_for(state=state, timeout=timeout)
                print(f"Selector ready: {args[0]} state={state}")

            elif cmd == "wait-for-url":
                timeout = int(args[1]) if len(args) > 1 else 10000
                await page.wait_for_url(args[0], timeout=timeout)
                print(f"URL matched: {page.url}")

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
