"""设置 / 类型管理 / 导出 三个对话框。"""

from __future__ import annotations

import os
import threading

import ttkbootstrap as tb
from tkinter import filedialog
from ttkbootstrap.dialogs.dialogs import Messagebox

from ..log import get_logger
from ..models import Level
from ..settings import SettingsManager
from ..utils import FileUtils

logger = get_logger("对话框")


class SettingsDialog(tb.Toplevel):
    """路径与开关设置。"""

    def __init__(self, parent: tb.Window, settings: SettingsManager) -> None:
        super().__init__()
        self.settings = settings
        self.title("设置")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.autoload_var = tb.BooleanVar(value=bool(settings.get("auto_load")))
        self.zip_folder_var = tb.StringVar(value=str(settings.get("zip_folder")))
        self.save_folder_var = tb.StringVar(value=str(settings.get("save_folder")))
        self.unzip_cache_folder_var = tb.StringVar(value=str(settings.get("unzip_cache_folder")))
        self.seven_zip_var = tb.StringVar(value=str(settings.get("seven_zip_path")))

        self.create_widgets()

    def on_close(self) -> None:
        self.destroy()

    # ------------------------------------------------------------------ 构建
    def _browse_folder(self, entry: tb.Entry) -> None:
        folder = filedialog.askdirectory(parent=self)
        if folder:
            entry.delete(0, "end")
            entry.insert(0, folder)
        self.focus_set()

    def _browse_7z(self, entry: tb.Entry) -> None:
        file_path = filedialog.askopenfilename(
            parent=self,
            title="选择 7z.exe",
            filetypes=[("7z 可执行文件", "7z.exe"), ("所有文件", "*.*")],
        )
        if file_path:
            entry.delete(0, "end")
            entry.insert(0, file_path)
        self.focus_set()

    def create_widgets(self) -> None:
        rows: list[tuple[str, str]] = [
            ("压缩包文件夹", "zip_folder"),
            ("保存路径", "save_folder"),
            ("缓存文件夹", "unzip_cache_folder"),
        ]

        frame = tb.Frame(self)
        frame.pack(fill="x", anchor="nw")
        for label, key in rows:
            box = tb.Labelframe(frame, text=label)
            box.pack(fill="x", padx=10, pady=10)
            entry = tb.Entry(box, textvariable=getattr(self, f"{key}_var"), width=80)
            entry.pack(side="left", padx=10, pady=10)
            tb.Button(
                box, text="浏览", bootstyle="primary", command=lambda e=entry: self._browse_folder(e)
            ).pack(side="left", padx=10)

        # 7z 路径：留空表示自动探测 Together 自带的 7z.exe
        box_7z = tb.Labelframe(frame, text="7z 路径（留空自动探测）")
        box_7z.pack(fill="x", padx=10, pady=10)
        entry_7z = tb.Entry(box_7z, textvariable=self.seven_zip_var, width=80)
        entry_7z.pack(side="left", padx=10, pady=10)
        tb.Button(
            box_7z, text="浏览", bootstyle="primary", command=lambda e=entry_7z: self._browse_7z(e)
        ).pack(side="left", padx=10)
        tb.Button(box_7z, text="自动探测", bootstyle="secondary", command=self._detect_7z).pack(
            side="left", padx=5
        )

        tb.Checkbutton(
            self, text="启动时自动加载", bootstyle="primary", variable=self.autoload_var
        ).pack(anchor="nw", padx=10, pady=10)

        buttons = tb.Frame(self)
        buttons.pack(fill="x", anchor="nw")
        tb.Button(buttons, text="保存", bootstyle="primary", command=self.save_settings).pack(
            side="left", padx=10, pady=10
        )
        tb.Button(buttons, text="取消", bootstyle="danger", command=self.on_close).pack(
            side="left", padx=10, pady=10
        )

    # ------------------------------------------------------------------ 动作
    def _detect_7z(self) -> None:
        found = FileUtils.get_7z_path()
        if found:
            self.seven_zip_var.set(found)
            Messagebox.show_info(f"已找到 7z：\n{found}", "自动探测", parent=self)
        else:
            Messagebox.show_warning(FileUtils.describe_7z_lookup(), "自动探测失败", parent=self)

    def save_settings(self) -> None:
        self.settings.change("auto_load", self.autoload_var.get())
        self.settings.change("zip_folder", self.zip_folder_var.get().strip())
        self.settings.change("save_folder", self.save_folder_var.get().strip())
        self.settings.change("unzip_cache_folder", self.unzip_cache_folder_var.get().strip())
        self.settings.change("seven_zip_path", self.seven_zip_var.get().strip())
        self.settings.save_settings()
        self.on_close()


class TypesDialog(tb.Toplevel):
    """关卡类型（导出时的分类目录名）管理。"""

    def __init__(self, parent: tb.Window, settings: SettingsManager) -> None:
        super().__init__()
        self.settings = settings
        self.title("类型管理")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_widgets()

    def on_close(self) -> None:
        self.destroy()

    def create_widgets(self) -> None:
        self.types_text = tb.Text(self, width=40, height=20)
        self.types_text.pack(fill="x", padx=10, pady=5)
        self.types_text.insert("1.0", "\n".join(self.settings.get("types") or []))

        buttons = tb.Frame(self)
        buttons.pack(fill="x", anchor="nw")
        tb.Button(buttons, text="保存", bootstyle="primary", command=self.save_types).pack(
            side="left", padx=10, pady=5
        )
        tb.Button(buttons, text="取消", bootstyle="danger", command=self.on_close).pack(
            side="left", padx=10, pady=5
        )

    def save_types(self) -> None:
        raw = self.types_text.get("1.0", "end-1c").split("\n")
        types = [line.strip() for line in raw if line.strip()]
        if not types:
            Messagebox.show_error("至少保留一个类型", "类型管理", parent=self)
            return
        self.settings.change("types", types)
        self.settings.save_settings()
        self.on_close()


class SavingDialog(tb.Toplevel):
    """把选中关卡解压导出到 ``保存路径/<类型>/``。"""

    def __init__(self, parent, settings: SettingsManager) -> None:
        super().__init__()
        self.parent_window = parent
        self.settings = settings
        self.title("保存")
        self.geometry("480x220")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.selected_items: tuple[str, ...] = parent.tree.selection()
        if not self.selected_items:
            logger.error("请先选择一个项目")
            Messagebox.show_error("请先选择一个项目", "错误", parent=parent)
            self.after(0, self.destroy)
            return

        types = list(settings.get("types") or ["Init"])
        self.types = types
        self.save_folder: str = str(settings.get("save_folder") or "")
        self.save_path_var = tb.StringVar()
        self.type_var = tb.StringVar(value=types[0])
        self.type_var.trace_add("write", self._update_save_path)
        self._update_save_path()
        self.create_widgets()

    def on_close(self) -> None:
        self.destroy()

    def _update_save_path(self, *_args) -> None:
        self.save_path_var.set(os.path.normpath(os.path.join(self.save_folder, self.type_var.get())))

    def create_widgets(self) -> None:
        box = tb.Labelframe(self, text="类型")
        box.pack(fill="x", padx=10, pady=5)
        tb.Combobox(box, textvariable=self.type_var, values=self.types, bootstyle="primary").pack(
            fill="x", padx=10, pady=5
        )
        tb.Label(box, textvariable=self.save_path_var).pack(fill="x", padx=10, pady=5)

        buttons = tb.Frame(self)
        buttons.pack(fill="x", anchor="nw")
        tb.Button(buttons, text="保存", bootstyle="primary", command=self.save_levels).pack(
            side="left", padx=10, pady=5
        )
        tb.Button(buttons, text="取消", bootstyle="danger", command=self.on_close).pack(
            side="left", padx=10, pady=5
        )

    def save_levels(self) -> None:
        bridge = self.parent_window.bridge
        tree = self.parent_window.tree
        target_root = self.save_path_var.get()
        seven_zip = str(self.settings.get("seven_zip_path") or "") or None
        items = list(self.selected_items)
        levels: list[Level] = [
            tree.level_map[item] for item in items if item in tree.level_map
        ]
        self.on_close()
        if not levels:
            return

        def worker() -> None:
            bridge.progress(0, len(levels))
            success = 0
            for index, level in enumerate(levels, start=1):
                if level.save(target_root, seven_zip=seven_zip):
                    success += 1
                bridge.status(f"保存 {success}/{len(levels)} 个关卡")
                bridge.progress(index, len(levels))
            bridge.status(f"保存完成：{success}/{len(levels)}")
            bridge.call(
                Messagebox.show_info,
                f"已保存 {success}/{len(levels)} 个关卡到\n{target_root}",
                "完成",
                self.parent_window,
            )

        threading.Thread(target=worker, daemon=True).start()
