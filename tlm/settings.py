"""设置（单例）。

* 设置文件位置见 :func:`tlm.paths.settings_path`（不再依赖当前工作目录）。
* 旧版本的 ``tl_settings_<ver>.json`` 会自动迁移。
* 新增的默认键会自动合并进旧文件，升级不会因为缺键 KeyError。
"""

from __future__ import annotations

import json
import os
import shutil

from .constants import DEFAULT_SETTINGS
from .log import get_logger
from .paths import legacy_settings_files, settings_path

logger = get_logger(__name__)


class SettingsManager:
    """全局设置管理器（单例）。"""

    _instance: "SettingsManager | None" = None
    _initialized: bool = False

    def __new__(cls) -> "SettingsManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if SettingsManager._initialized:
            return
        self.settings: dict = {}
        self.path = settings_path()
        self.load_settings()
        SettingsManager._initialized = True

    # ------------------------------------------------------------------ 生命周期
    @classmethod
    def reset(cls) -> None:
        """丢弃单例（测试或切换 TLM_HOME 时使用）。"""
        cls._instance = None
        cls._initialized = False

    # ------------------------------------------------------------------ 读写
    def load_settings(self) -> None:
        logger.info("加载设置")
        self.path = settings_path()
        if not self.path.exists():
            self._migrate_legacy()

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                raise json.JSONDecodeError("设置文件根节点不是对象", "", 0)
            self.settings = loaded
            self._apply_defaults()
            logger.info(f"设置加载成功: {self.path}")
            self.create_folder()
            return
        except FileNotFoundError:
            logger.warning(f"设置文件不存在，将使用默认设置: {self.path}")
        except json.JSONDecodeError as exc:
            logger.error(f"设置文件格式错误（{self.path}）: {exc}；已改用默认设置")
        except OSError as exc:
            logger.error(f"读取设置失败（{self.path}）: {exc}；已改用默认设置")

        self.settings = {k: (v.copy() if isinstance(v, list) else v) for k, v in DEFAULT_SETTINGS.items()}
        self.save_settings()

    def save_settings(self) -> None:
        logger.info("保存设置")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            self.create_folder()
        except OSError as exc:
            logger.error(f"保存设置失败（{self.path}）: {exc}")
        except TypeError as exc:
            logger.error(f"设置内容无法序列化: {exc}")

    def change(self, key: str, value) -> None:
        """修改一个设置项（不落盘，需再调 :meth:`save_settings`）。"""
        if key not in DEFAULT_SETTINGS:
            logger.warning(f"设置项 {key} 不在默认表中，仍然写入")
        self.settings[key] = value

    def get(self, key: str, default=None):
        return self.settings.get(key, DEFAULT_SETTINGS.get(key, default))

    # ------------------------------------------------------------------ 辅助
    def _apply_defaults(self) -> None:
        for key, default in DEFAULT_SETTINGS.items():
            if key not in self.settings:
                self.settings[key] = default.copy() if isinstance(default, list) else default

    def _migrate_legacy(self) -> None:
        """把旧版设置文件搬到新路径。"""
        for old in legacy_settings_files():
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old, self.path)
                logger.info(f"已从旧设置文件迁移: {old} -> {self.path}")
                return
            except OSError as exc:
                logger.warning(f"迁移旧设置文件失败（{old}）: {exc}")

    def create_folder(self) -> None:
        """创建设置里指定的目录（缓存 / 保存路径）。"""
        for key in ("unzip_cache_folder", "save_folder"):
            folder = self.settings.get(key)
            if not folder:
                continue
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError as exc:
                logger.error(f"创建目录失败（{folder}）: {exc}")
