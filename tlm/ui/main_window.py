"""主窗口。"""

from __future__ import annotations

import threading
from typing import Any

import ttkbootstrap as tb
from ttkbootstrap.dialogs.dialogs import Messagebox

from ..constants import THEMENAME, VERSION
from ..log import get_logger
from ..models import Level
from ..service import LevelManager
from ..settings import SettingsManager
from ..utils import FileUtils
from .bridge import UiBridge
from .dialogs import SavingDialog, SettingsDialog, TypesDialog
from .treeview import TreeViewHelper

logger = get_logger("主窗口")


class UI(tb.Window):
    """程序主窗口。"""

    COLUMNS: tuple[str, ...] = ("song", "artist", "author", "date")
    HEADERS: tuple[str, ...] = ("歌曲", "艺术家", "作者", "日期")
    WIDTHS: tuple[int, ...] = (200, 350, 200, 150)
    ANCHORS: tuple[str, ...] = ("w", "w", "w", "w")

    def __init__(self, settings: SettingsManager | None = None) -> None:
        super().__init__(themename=THEMENAME)
        self.settings = settings or SettingsManager()
        self.title(f"Together Level Manager v{VERSION}")
        self.geometry("1000x600")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.level_data: list[Level] = []
        self.status_var = tb.StringVar()
        self.bridge = UiBridge(self, self._apply_ui_event)
        self.settings_window: SettingsDialog | None = None

        self.create_widgets()
        self._refresh_status_bar()

        if self.settings.get("auto_load"):
            self.refresh_levels()

    # ------------------------------------------------------------------ 生命周期
    def on_close(self) -> None:
        logger.info("关闭程序")
        try:
            self.bridge.close()
        finally:
            self.destroy()

    def _refresh_status_bar(self) -> None:
        self.status_var.set(f"就绪 | 找到 {len(self.level_data)} 个关卡")

    # ------------------------------------------------------------- 线程 → UI
    def _apply_ui_event(self, kind: str, payload: Any) -> None:
        if kind == "status":
            self.status_var.set(str(payload))
        elif kind == "progress":
            value, maximum = payload
            self._set_progress(value, maximum)
        elif kind == "call":
            func, args = payload
            func(*args)

    def _set_progress(self, value: int, maximum: int) -> None:
        maximum = max(1, int(maximum))
        if int(self.progress["maximum"]) != maximum:
            self.progress["maximum"] = maximum
        self.progress["value"] = min(max(0, int(value)), maximum)

    # ------------------------------------------------------------------ 构建
    def create_widgets(self) -> None:
        toolbar = tb.Labelframe(self, text="工具栏")
        toolbar.pack(fill="x", pady=5)

        buttons: list[tuple[str, Any]] = [
            ("设置", self.open_settings),
            ("刷新", self.refresh_levels),
            ("保存", self.open_saving),
            ("清理缓存", self.clear_cache),
            ("管理类型", self.open_types_manager),
        ]
        for text, command in buttons:
            tb.Button(toolbar, text=text, command=command, bootstyle="primary").pack(
                side="left", padx=5, pady=5
            )

        frame = tb.Frame(self)
        frame.pack(fill="both", expand=True)
        self.tree, scroller = TreeViewHelper.setup_treeview(
            frame, self.COLUMNS, self.HEADERS, self.WIDTHS, self.ANCHORS
        )
        for col in self.COLUMNS:
            self.tree.heading(
                col,
                text=self.HEADERS[self.COLUMNS.index(col)],
                command=lambda c=col: TreeViewHelper.sort_treeview(self.tree, c),
            )
        TreeViewHelper.sort_treeview(self.tree, "date")
        self.tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scroller.pack(side="right", fill="y", pady=5)

        self.progress = tb.Progressbar(
            self, bootstyle="success-striped", orient="horizontal", mode="determinate"
        )
        self.progress.pack(fill="x", pady=10)

        self.status_bar = tb.Label(
            self,
            textvariable=self.status_var,
            relief="flat",
            anchor="w",
            padding=(10, 5),
            bootstyle="inverse-primary",
        )
        self.status_bar.pack(side="bottom", fill="x")

    # ------------------------------------------------------------------ 弹窗
    def open_settings(self) -> None:
        window = SettingsDialog(self, self.settings)
        self.settings_window = window
        self.after(0, window.focus)

    def open_types_manager(self) -> None:
        window = TypesDialog(self, self.settings)
        self.types_manager_window = window
        self.after(0, window.focus)

    def open_saving(self) -> None:
        window = SavingDialog(self, self.settings)
        self.saving_window = window
        if window.winfo_exists():
            self.after(0, window.focus)

    # ------------------------------------------------------------------ 动作
    def _require_folders(self) -> bool:
        missing = [
            label
            for label, key in (
                ("压缩包文件夹", "zip_folder"),
                ("解压缓存文件夹", "unzip_cache_folder"),
            )
            if not self.settings.get(key)
        ]
        if missing:
            message = "请先设置：" + "、".join(missing)
            logger.error(message)
            self.status_var.set(message)
            Messagebox.show_error(message, "错误", parent=self)
            return False
        return True

    def refresh_levels(self) -> None:
        if not self._require_folders():
            return

        self.level_data = []
        self.tree.delete(*self.tree.get_children(""))
        self.tree.level_map.clear()
        self.status_var.set("正在刷新关卡...")

        bridge = self.bridge
        zip_folder = str(self.settings.get("zip_folder"))
        cache_folder = str(self.settings.get("unzip_cache_folder"))
        seven_zip = str(self.settings.get("seven_zip_path") or "") or None

        def worker() -> None:
            logger.info("开始刷新关卡")
            try:
                manager = LevelManager(
                    zip_folder=zip_folder,
                    cache_folder=cache_folder,
                    seven_zip=seven_zip,
                    on_status=bridge.status,
                    on_progress=bridge.progress,
                )
                levels = manager.load_levels()
            except Exception as exc:  # noqa: BLE001
                logger.error(f"刷新关卡时发生未知错误: {exc}")
                bridge.status("刷新关卡失败")
                bridge.call(Messagebox.show_error, f"刷新关卡时发生未知错误: {exc}", "错误", self)
                return
            bridge.call(self._render_levels, levels)

        threading.Thread(target=worker, daemon=True).start()

    def _render_levels(self, levels: list[Level]) -> None:
        """主线程：把加载结果灌进表格。"""
        self.level_data = levels
        self.tree.delete(*self.tree.get_children(""))
        self.tree.level_map.clear()
        TreeViewHelper.populate_treeview(self.tree, levels)
        self._refresh_status_bar()

    def clear_cache(self) -> None:
        if not self.settings.get("unzip_cache_folder"):
            message = "请先设置解压缓存文件夹"
            logger.error(message)
            self.status_var.set(message)
            Messagebox.show_error(message, "错误", parent=self)
            return

        cache_folder = str(self.settings.get("unzip_cache_folder"))
        self.status_var.set("正在清理缓存...")
        bridge = self.bridge

        def worker() -> None:
            logger.info("开始清理缓存")
            try:
                FileUtils.clear_directory(cache_folder)
                logger.info(f"成功清理缓存文件夹: {cache_folder}")
            except Exception as exc:  # noqa: BLE001
                logger.error(f"清理缓存时发生未知错误: {exc}")
                bridge.status("清理缓存失败")
                bridge.call(Messagebox.show_error, f"清理缓存时发生未知错误: {exc}", "错误", self)
                return
            bridge.call(self._after_clear_cache)

        threading.Thread(target=worker, daemon=True).start()

    def _after_clear_cache(self) -> None:
        self._refresh_status_bar()
        self.status_var.set("缓存已清理")
