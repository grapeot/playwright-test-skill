"""Unit tests for pw-test CLI argument parsing and command dispatch.

These tests verify argument validation and command routing without requiring
a live CDP connection.
"""
from __future__ import annotations

import pytest

from playwright_test_skill.cli import main, async_main, CDP_URL, USAGE


def test_no_args_prints_usage_and_returns_1(capsys):
    rc = main([])
    assert rc == 1
    captured = capsys.readouterr()
    assert "Usage:" in captured.err
    assert "pw-test" in captured.err


def test_cdp_url_default():
    assert CDP_URL == "http://localhost:9222"


def test_usage_contains_all_commands():
    for cmd in ["goto", "click", "fill", "snapshot", "wait", "reload", "eval", "url", "title", "screenshot", "storage"]:
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