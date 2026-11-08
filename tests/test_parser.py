"""``.adofai`` 解析与修复的回归测试。"""

from __future__ import annotations

import json

import pytest

from tlm.parser import Parser


def _write(tmp_path, payload: str, name: str = "main.adofai"):
    path = tmp_path / name
    path.write_text(payload, encoding="utf-8")
    return str(path)


def test_path_data_is_converted_to_angle_data(tmp_path):
    chart = {"settings": {"song": "s"}, "pathData": "RRUL"}
    parser = Parser(_write(tmp_path, json.dumps(chart)))
    assert parser()["angleData"] == [0, 0, 90, 180]


def test_relative_path_characters_use_previous_angle(tmp_path):
    chart = {"pathData": "R5"}  # 0 -> +72
    parser = Parser(_write(tmp_path, json.dumps(chart)))
    assert parser()["angleData"] == [0, 72]

    chart = {"pathData": "U6"}  # 90 -> -72
    parser = Parser(_write(tmp_path, json.dumps(chart)))
    assert parser()["angleData"] == [90, 18]


def test_pause_marker_maps_to_999(tmp_path):
    parser = Parser(_write(tmp_path, json.dumps({"pathData": "R!"})))
    assert parser()["angleData"] == [0, 999]


def test_unknown_operator_raises(tmp_path):
    chart = {"pathData": "R?"}
    with pytest.raises(ValueError):
        Parser(_write(tmp_path, json.dumps(chart)))


def test_bom_and_trailing_comma_are_repaired(tmp_path):
    payload = '\ufeff{"settings": {"song": "x",}, "angleData": [0,]}'
    parser = Parser(_write(tmp_path, payload))
    assert parser()["settings"]["song"] == "x"
    assert parser()["angleData"] == [0]


def test_truncated_json_is_repaired(tmp_path):
    payload = '{"settings": {"song": "cut", "artist": "a"}, "angleData": [0, 90'
    parser = Parser(_write(tmp_path, payload))
    data = parser()
    assert data["settings"]["song"] == "cut"
    assert data["angleData"] == [0, 90]


def test_existing_angle_data_is_not_overwritten(tmp_path):
    chart = {"pathData": "RRRR", "angleData": [11, 22]}
    parser = Parser(_write(tmp_path, json.dumps(chart)))
    assert parser()["angleData"] == [11, 22]


def test_garbage_returns_empty_dict(tmp_path):
    parser = Parser(_write(tmp_path, "not json at all"))
    assert parser() == {}
