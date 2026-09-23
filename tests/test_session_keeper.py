"""Tests for session_keeper_refresher (no network, no browser)."""
import base64
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "session_keeper_refresher", REPO / "scripts" / "session_keeper_refresher.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["session_keeper_refresher"] = mod
spec.loader.exec_module(mod)


def make_jwt(exp: int, user_id: int = 42) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp, "user_id": user_id}).encode()).decode().rstrip("=")
    return f"{header}.{payload}.sig"


class TestMask:
    def test_long_value(self):
        assert mod.mask("abcdefghij1234567890") == "abcdefgh...567890(20)"

    def test_empty(self):
        assert mod.mask("") == "<empty>"


class TestDecodeJwt:
    def test_valid(self):
        exp, uid = mod.decode_jwt(make_jwt(1795366884, 42))
        assert exp == 1795366884
        assert uid == 42

    def test_not_a_jwt(self):
        assert mod.decode_jwt("garbage") == (None, None)


class TestUpdateEnv:
    def _run(self, tmpdir, existing_lines):
        target = os.path.join(tmpdir, ".env")
        open(target, "w").write("".join(existing_lines))
        values = {"Authorization": "NEWAUTH", "Session": "NEWSESSION", "Account": "NEWACCOUNT"}
        changed, bak = mod.update_env(target, values)
        result = open(target).read()
        return changed, bak, result, target

    def test_replaces_and_appends(self, tmp_path):
        lines = ["EXAMPLE_AUTHORIZATION=old\n", "OTHER=keep\n"]
        changed, bak, result, target = self._run(str(tmp_path), lines)
        assert "EXAMPLE_AUTHORIZATION" in changed
        assert "EXAMPLE_SESSION" in changed  # appended
        assert "OTHER=keep" in result
        assert "EXAMPLE_AUTHORIZATION=NEWAUTH" in result
        assert os.path.exists(bak)
        assert "old" in open(bak).read()

    def test_idempotent_values_reported_by_caller(self, tmp_path):
        # update_env itself always writes; the no_change gate lives in do_capture
        lines = ["EXAMPLE_AUTHORIZATION=NEWAUTH\n", "EXAMPLE_SESSION=NEWSESSION\n", "EXAMPLE_ACCOUNT=NEWACCOUNT\n"]
        target = os.path.join(str(tmp_path), ".env")
        open(target, "w").write("".join(lines))
        values = {"Authorization": "NEWAUTH", "Session": "NEWSESSION", "Account": "NEWACCOUNT"}
        var_map = mod.SITE["env_field_map"]
        old = {v: mod.env_var(target, v) for v in var_map.values()}
        new = {v: values[f] for f, v in var_map.items()}
        assert old == new  # caller would report no_change without calling update_env


class TestEnvVar:
    def test_found(self, tmp_path):
        target = os.path.join(str(tmp_path), ".env")
        open(target, "w").write("EXAMPLE_AUTHORIZATION=abc123\nOTHER=x\n")
        assert mod.env_var(target, "EXAMPLE_AUTHORIZATION") == "abc123"

    def test_missing_file(self):
        assert mod.env_var("/nonexistent/.env", "X", "dflt") == "dflt"


class TestSiteConfig:
    def test_no_real_credentials(self):
        cfg = mod.SITE
        assert "example.com" in cfg["url"]
        assert "typefully" not in json.dumps(cfg).lower()
        assert cfg["account_fallback"] == "replace-with-account-id"
        assert all("EXAMPLE_" in v for v in cfg["env_field_map"].values())

    def test_verify_url_present(self):
        assert mod.SITE["verify_url"].startswith("https://")