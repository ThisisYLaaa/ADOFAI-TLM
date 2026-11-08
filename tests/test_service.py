"""``LevelManager`` 扫描逻辑测试（不依赖 GUI，也不依赖 7z）。"""

from __future__ import annotations

import json

from tlm.service import LevelManager


def _make_level(folder, name="main.adofai", song="S"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(
        json.dumps({"settings": {"song": song, "artist": "A", "author": "N"}, "angleData": [0, 90]}),
        encoding="utf-8",
    )


def test_no_archives_reports_status(tmp_path):
    statuses: list[str] = []
    zip_dir = tmp_path / "zip"
    cache_dir = tmp_path / "cache"
    zip_dir.mkdir()
    cache_dir.mkdir()

    manager = LevelManager(str(zip_dir), str(cache_dir), on_status=statuses.append)
    manager.process_archives()
    assert any("没有需要处理的压缩包" in s for s in statuses)


def test_scan_levels_collects_levels(tmp_path):
    cache_dir = tmp_path / "cache"
    _make_level(cache_dir / "chart_a", song="Alpha")
    _make_level(cache_dir / "chart_b", song="Beta")

    manager = LevelManager(str(tmp_path / "zip"), str(cache_dir))
    manager.scan_levels()
    assert sorted(level.song for level in manager.levels) == ["Alpha", "Beta"]


def test_scan_skips_hidden_directories(tmp_path):
    cache_dir = tmp_path / "cache"
    _make_level(cache_dir / "chart_a", song="Alpha")
    _make_level(cache_dir / ".hidden", song="Hidden")

    manager = LevelManager(str(tmp_path / "zip"), str(cache_dir))
    manager.scan_levels()
    assert [level.song for level in manager.levels] == ["Alpha"]


def test_scan_missing_cache_folder_is_reported(tmp_path):
    statuses: list[str] = []
    manager = LevelManager(str(tmp_path / "zip"), str(tmp_path / "nope"), on_status=statuses.append)
    manager.scan_levels()
    assert manager.levels == []
    assert any("缓存目录不存在" in s for s in statuses)


def test_progress_callback_counts_items(tmp_path):
    cache_dir = tmp_path / "cache"
    _make_level(cache_dir / "a")
    _make_level(cache_dir / "b")
    seen: list[tuple[int, int]] = []

    manager = LevelManager(str(tmp_path / "zip"), str(cache_dir), on_progress=lambda v, m: seen.append((v, m)))
    manager.scan_levels()
    assert seen[0] == (0, 2)
    assert seen[-1] == (2, 2)


def test_levels_without_adofai_are_ignored(tmp_path):
    cache_dir = tmp_path / "cache"
    (cache_dir / "empty_dir").mkdir(parents=True)
    _make_level(cache_dir / "ok")

    manager = LevelManager(str(tmp_path / "zip"), str(cache_dir))
    manager.scan_levels()
    assert len(manager.levels) == 1
