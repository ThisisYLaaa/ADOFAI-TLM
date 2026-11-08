"""树形视图与排序。"""

from __future__ import annotations

import tkinter as tk

import ttkbootstrap as tb

from ..constants import WHEEL_SCROLL_UNIT
from ..models import Level


class CustomTreeview(tb.Treeview):
    """在 Treeview 上挂一个 ``level_map``：item id -> Level 对象。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.level_map: dict[str, Level] = {}


class TreeViewHelper:
    """树的创建、排序、填充。"""

    #: 每棵树（按 id）的排序列状态
    _sort_states: dict[int, dict[str, bool]] = {}
    _last_sorted_col: dict[int, str | None] = {}

    # ------------------------------------------------------------------ 创建
    @staticmethod
    def setup_treeview(
        parent: tk.Misc,
        columns: tuple[str, ...],
        headings: tuple[str, ...],
        widths: tuple[int, ...],
        anchors: tuple[str, ...],
        selectmode: str = "extended",
        bootstyle: str = "primary",
    ) -> tuple[CustomTreeview, tb.Scrollbar]:
        tree = CustomTreeview(
            parent,
            columns=columns,
            show="headings",
            selectmode=selectmode,
            bootstyle=bootstyle,
        )
        for col, heading, width, anchor in zip(columns, headings, widths, anchors):
            tree.heading(col, text=heading)
            tree.column(col, width=width, anchor=anchor)

        scrollbar = tb.Scrollbar(parent, orient="vertical", command=tree.yview, bootstyle="round")
        tree.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event: tk.Event) -> None:
            if event.delta:
                tree.yview_scroll(int(-1 * (event.delta / 120) * WHEEL_SCROLL_UNIT), "units")

        tree.bind("<MouseWheel>", _on_mousewheel)
        return tree, scrollbar

    # ------------------------------------------------------------------ 排序
    @staticmethod
    def sort_treeview(tree: CustomTreeview, col: str) -> None:
        """点击列头排序：新列升序，同列切换升降序，表头带箭头。"""
        tree_id = id(tree)
        TreeViewHelper._sort_states.setdefault(tree_id, {})
        TreeViewHelper._last_sorted_col.setdefault(tree_id, None)

        if TreeViewHelper._last_sorted_col[tree_id] != col:
            reverse = False
            TreeViewHelper._sort_states[tree_id][col] = True
            TreeViewHelper._last_sorted_col[tree_id] = col
        else:
            reverse = TreeViewHelper._sort_states[tree_id].get(col, False)
            TreeViewHelper._sort_states[tree_id][col] = not reverse

        items = [(tree.set(child, col), child) for child in tree.get_children("")]
        items.sort(reverse=reverse)
        for index, (_value, child) in enumerate(items):
            tree.move(child, "", index)

        TreeViewHelper._update_headings(tree, col, reverse)

    @staticmethod
    def _update_headings(tree: CustomTreeview, col: str, reverse: bool) -> None:
        for current in tree["columns"]:
            text = str(tree.heading(current, "text"))
            if text.endswith((" ↑", " ↓")):
                text = text[:-2]
            if current == col:
                text += " ↓" if reverse else " ↑"
            tree.heading(current, text=text)

    # ------------------------------------------------------------------ 填充
    @staticmethod
    def populate_treeview(tree: CustomTreeview, data: list[Level]) -> None:
        """填充表格（调用前请自行清空），并按日期排一次序。"""
        for item in data:
            item_id = tree.insert("", "end", values=item.get_display_values())
            tree.level_map[item_id] = item
        TreeViewHelper.sort_treeview(tree, "date")
