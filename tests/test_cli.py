"""Unit tests for pw-test CLI argument parsing and command dispatch.

These tests verify argument validation and command routing without requiring
a live CDP connection.
"""
from __future__ import annotations

import pytest

from playwright_test_skill.cli import main, async_main, CDP_URL, USAGE


class FakePage:
    url = "https://example.com/current"

    async def title(self):
        return "Example"

    async def evaluate(self, _script):
        return None


class FakeContext:
    pages = [FakePage()]


class FakeBrowser:
    contexts = [FakeContext()]


class FakeChromium:
    async def connect_over_cdp(self, _url):
        return FakeBrowser()


class FakePlaywright:
    chromium = FakeChromium()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


def test_no_args_prints_usage_and_returns_1(capsys):
    rc = main([])
    assert rc == 1
    captured = capsys.readouterr()
    assert "Usage:" in captured.err
    assert "pw-test" in captured.err


def test_cdp_url_default():
    assert CDP_URL == "http://localhost:9222"


def test_usage_contains_all_commands():
    for cmd in [
        "goto",
        "click",
        "fill",
        "snapshot",
        "diagnose",
        "elements",
        "wait-for-selector",
        "wait-for-url",
        "wait",
        "reload",
        "eval",
        "url",
        "title",
        "screenshot",
        "storage",
    ]:
        assert cmd in USAGE


@pytest.mark.asyncio
async def test_goto_requires_url(capsys):
    rc = await async_main(["goto"])
    assert rc == 1
    assert "requires a URL" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_click_requires_selector(capsys):
    rc = await async_main(["click"])
    assert rc == 1
    assert "requires a selector" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_fill_requires_two_args(capsys):
    rc = await async_main(["fill"])
    assert rc == 1
    assert "requires" in capsys.readouterr().err

    rc2 = await async_main(["fill", "input"])
    assert rc2 == 1


@pytest.mark.asyncio
async def test_wait_requires_duration(capsys):
    rc = await async_main(["wait"])
    assert rc == 1
    assert "duration" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_eval_requires_expression(capsys):
    rc = await async_main(["eval"])
    assert rc == 1
    assert "JavaScript" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_screenshot_requires_path(capsys):
    rc = await async_main(["screenshot"])
    assert rc == 1
    assert "file path" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_elements_requires_selector(capsys):
    rc = await async_main(["elements"])
    assert rc == 1
    assert "selector" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_wait_for_selector_requires_selector(capsys):
    rc = await async_main(["wait-for-selector"])
    assert rc == 1
    assert "selector" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_wait_for_url_requires_pattern(capsys):
    rc = await async_main(["wait-for-url"])
    assert rc == 1
    assert "URL pattern" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_valid_command_runs_cdp_flow(monkeypatch, capsys):
    monkeypatch.setattr("playwright.async_api.async_playwright", lambda: FakePlaywright())

    rc = await async_main(["url"])

    assert rc == 0
    assert "https://example.com/current" in capsys.readouterr().out
