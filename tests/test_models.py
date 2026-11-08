"""``Level`` 模型测试（含旧版崩溃点的回归用例）。"""

from __future__ import annotations

import json
import os
import time

from tlm.models import Level


def _chart(tmp_path, name="main.adofai", song="歌名", artist="艺术家", author="作者", angles=(0, 90)):
    path = tmp_path / name
    path.write_text(
        json.dumps(
            {"settings": {"song": song, "artist": artist, "author": author}, "angleData": list(angles)}
        ),
        encoding="utf-8",
    )
    return str(path)


def test_level_without_archive_does_not_crash(tmp_path):
    """旧实现在目录里没有压缩包时会漏赋 self.date，随后抛 AttributeError。"""
    level = Level(_chart(tmp_path))
    assert level.date == "unknown"
    assert level.archive_path == ""
    assert level.size == 2


def test_level_uses_archive_mtime_as_date(tmp_path):
    archive = tmp_path / "level.zip"
    archive.write_bytes(b"PK\x03\x04fake")
    stamp = time.mktime((2024, 5, 6, 7, 8, 9, 0, 0, -1))
    os.utime(archive, (stamp, stamp))

    level = Level(_chart(tmp_path))
    assert level.archive_path.endswith("level.zip")
    assert level.date.startswith("2024-05-06")


def test_song_falls_back_to_audio_file_name(tmp_path):
    (tmp_path / "MySong.ogg").write_bytes(b"OggS")
    level = Level(_chart(tmp_path, song=""))
    assert level.song == "MySong"


def test_missing_metadata_falls_back_to_unknown(tmp_path):
    level = Level(_chart(tmp_path, song="", artist="", author=""))
    assert (level.song, level.artist, level.author) == ("unknown", "unknown", "unknown")


def test_unity_rich_text_is_stripped(tmp_path):
    level = Level(_chart(tmp_path, song="<color=#fff>标题</color>", artist="A<b>B</b>"))
    assert level.song == "标题"
    assert level.artist == "AB"


def test_display_values_order(tmp_path):
    level = Level(_chart(tmp_path, song="S", artist="A", author="N"))
    assert level.get_display_values() == ("S", "A", "N", "unknown")


def test_save_without_archive_returns_false(tmp_path):
    level = Level(_chart(tmp_path))
    assert level.save(str(tmp_path / "out")) is False
