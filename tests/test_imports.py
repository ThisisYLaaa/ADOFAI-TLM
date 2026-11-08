"""GUI 模块的导入冒烟测试。

目的：在没有显示环境 / 没装 ttkbootstrap 的机器上，也能验证
``tlm.ui.*`` 的模块级代码与类定义没有语法/名字错误。

做法：把 ``ttkbootstrap`` 换成一个只提供"可被继承的空壳类"的假模块。
真正的窗口行为不在这里验证（那是 GUI 手工测试的事）。
"""

from __future__ import annotations

import sys
import types

import pytest

pytest.importorskip("tkinter")


class _Widget:
    """能接受任意构造参数的假控件。"""

    def __init__(self, *args, **kwargs) -> None:
        self._options: dict = dict(kwargs)

    def __getitem__(self, key):
        return self._options.get(key)

    def __setitem__(self, key, value):
        self._options[key] = value

    def pack(self, *args, **kwargs) -> None:
        return None

    def heading(self, *args, **kwargs) -> None:
        return None

    def column(self, *args, **kwargs) -> None:
        return None

    def configure(self, *args, **kwargs) -> None:
        return None


class _Var:
    def __init__(self, *args, **kwargs) -> None:
        self._value = kwargs.get("value")

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value

    def trace_add(self, *args, **kwargs) -> None:
        return None


def _fake_ttkbootstrap() -> types.ModuleType:
    module = types.ModuleType("ttkbootstrap")
    for name in (
        "Window",
        "Toplevel",
        "Frame",
        "Labelframe",
        "Entry",
        "Button",
        "Checkbutton",
        "Text",
        "Combobox",
        "Label",
        "Progressbar",
        "Treeview",
        "Scrollbar",
    ):
        setattr(module, name, type(name, (_Widget,), {}))
    for name in ("BooleanVar", "StringVar", "IntVar"):
        setattr(module, name, type(name, (_Var,), {}))

    dialogs = types.ModuleType("ttkbootstrap.dialogs")
    dialogs_dialogs = types.ModuleType("ttkbootstrap.dialogs.dialogs")

    class Messagebox:
        @staticmethod
        def show_info(*args, **kwargs):
            return None

        @staticmethod
        def show_error(*args, **kwargs):
            return None

        @staticmethod
        def show_warning(*args, **kwargs):
            return None

    dialogs_dialogs.Messagebox = Messagebox
    dialogs.dialogs = dialogs_dialogs
    module.dialogs = dialogs
    return module


@pytest.fixture()
def fake_tb(monkeypatch):
    fake = _fake_ttkbootstrap()
    monkeypatch.setitem(sys.modules, "ttkbootstrap", fake)
    monkeypatch.setitem(sys.modules, "ttkbootstrap.dialogs", fake.dialogs)
    monkeypatch.setitem(sys.modules, "ttkbootstrap.dialogs.dialogs", fake.dialogs.dialogs)
    # 让已缓存的模块重新导入
    for name in list(sys.modules):
        if name.startswith("tlm.ui"):
            monkeypatch.delitem(sys.modules, name, raising=False)
    return fake


def test_ui_modules_import(fake_tb):
    from tlm.ui.main_window import UI

    assert UI.COLUMNS == ("song", "artist", "author", "date")
    assert hasattr(UI, "refresh_levels")


def test_bridge_imports_without_tk_root():
    from tlm.ui.bridge import UiBridge

    assert UiBridge.DRAIN_BATCH > 0


def test_dialogs_import(fake_tb):
    from tlm.ui import dialogs

    assert hasattr(dialogs, "SettingsDialog")
    assert hasattr(dialogs, "SavingDialog")
    assert hasattr(dialogs, "TypesDialog")
