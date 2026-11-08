"""工具函数测试。"""

from __future__ import annotations

import os

import pytest

from tlm.utils import FileUtils, HtmlUtils


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("歌名_艺术家_作者", "歌名_艺术家_作者"),
        ('a/b\\c:d*e?f"g<h>i|j', "abcdefghij"),
        ("   ", "未知关卡"),
        ("", "未知关卡"),
    ],
)
def test_sanitize_filename(raw, expected):
    assert FileUtils.sanitize_filename(raw) == expected


def test_clean_html_tags_strips_unity_markup():
    assert HtmlUtils.clean_html_tags("<color=#ff0000>红</color>") == "红"
    assert HtmlUtils.clean_html_tags("a<b>粗</b>c") == "a粗c"
    assert HtmlUtils.clean_html_tags("&amp;") == "&"
    assert HtmlUtils.clean_html_tags(None) is None


def test_list_archives_filters_and_ignores_subdirs(tmp_path):
    (tmp_path / "a.zip").write_bytes(b"x")
    (tmp_path / "b.7z").write_bytes(b"x")
    (tmp_path / "c.txt").write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "d.zip").write_bytes(b"x")

    found = sorted(FileUtils.list_archives(str(tmp_path)))
    assert found == ["a.zip", "b.7z"]


def test_list_archives_on_missing_folder_returns_empty():
    assert FileUtils.list_archives(str(os.path.join("Z:", "nope"))) == []


def test_clear_directory_removes_files_but_keeps_root(tmp_path):
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "g.txt").write_text("x", encoding="utf-8")

    FileUtils.clear_directory(str(tmp_path))
    assert tmp_path.exists()
    assert list(tmp_path.iterdir()) == []


def test_find_7z_prefers_explicit_path(tmp_path, monkeypatch):
    """显式指定的可执行文件优先级最高。"""
    monkeypatch.delenv("TLM_7Z", raising=False)
    fake = tmp_path / "7z.exe"
    fake.write_bytes(b"stub")

    from tlm.paths import find_7z

    assert find_7z(str(fake)) == str(fake)


def test_find_7z_honours_env_override(tmp_path, monkeypatch):
    fake = tmp_path / "7z-env.exe"
    fake.write_bytes(b"stub")
    monkeypatch.setenv("TLM_7Z", str(fake))

    from tlm.paths import find_7z

    assert find_7z() == str(fake)


def test_probe_7z_reports_candidates():
    from tlm.paths import probe_7z

    probed = probe_7z()
    assert probed, "候选列表不应为空"
    assert all(isinstance(path, str) and isinstance(ok, bool) for path, ok in probed)
    assert any(path.lower().endswith("7z.exe") for path, _ in probed)


def test_describe_7z_lookup_is_helpful():
    text = FileUtils.describe_7z_lookup()
    assert "7z.exe" in text
    assert "TLM_7Z" in text
