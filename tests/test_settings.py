"""设置读写测试（含旧文件迁移）。"""

from __future__ import annotations

import json

import pytest

from tlm.constants import DEFAULT_SETTINGS
from tlm.paths import SETTINGS_FILENAME, settings_path
from tlm.settings import SettingsManager


@pytest.fixture()
def tlm_home(tmp_path, monkeypatch):
    monkeypatch.setenv("TLM_HOME", str(tmp_path))
    SettingsManager.reset()
    yield tmp_path
    SettingsManager.reset()


def test_defaults_are_written_on_first_run(tlm_home):
    sm = SettingsManager()
    path = tlm_home / SETTINGS_FILENAME
    assert path.exists()
    for key in DEFAULT_SETTINGS:
        assert key in sm.settings
    assert sm.get("auto_load") is False


def test_save_and_reload_roundtrip(tlm_home):
    sm = SettingsManager()
    sm.change("zip_folder", "C:/levels")
    sm.change("types", ["A", "B"])
    sm.save_settings()

    SettingsManager.reset()
    again = SettingsManager()
    assert again.get("zip_folder") == "C:/levels"
    assert again.get("types") == ["A", "B"]


def test_unknown_key_is_not_lost(tlm_home):
    sm = SettingsManager()
    sm.change("custom_key", 42)
    sm.save_settings()

    SettingsManager.reset()
    assert SettingsManager().get("custom_key") == 42


def test_missing_keys_are_merged_from_defaults(tlm_home):
    (tlm_home / SETTINGS_FILENAME).write_text(json.dumps({"zip_folder": "X"}), encoding="utf-8")
    SettingsManager.reset()
    sm = SettingsManager()
    assert sm.get("zip_folder") == "X"
    assert "seven_zip_path" in sm.settings


def test_corrupted_settings_file_falls_back_to_defaults(tlm_home):
    (tlm_home / SETTINGS_FILENAME).write_text("{not json", encoding="utf-8")
    SettingsManager.reset()
    sm = SettingsManager()
    assert sm.get("zip_folder") == ""
    assert sm.get("types") == ["Init"]


def test_legacy_settings_are_migrated(tlm_home):
    legacy = tlm_home / "tl_settings_1.0.0.json"
    legacy.write_text(json.dumps({"zip_folder": "OLD"}), encoding="utf-8")

    SettingsManager.reset()
    sm = SettingsManager()
    assert sm.get("zip_folder") == "OLD"
    assert settings_path().exists()


def test_get_falls_back_to_default(tlm_home):
    sm = SettingsManager()
    assert sm.get("not_a_key", "fallback") == "fallback"
