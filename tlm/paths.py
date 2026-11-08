"""路径探测：配置文件位置、Together 安装目录与 7z.exe。

设计目标
--------
1. **不依赖当前工作目录**：以前设置文件是相对路径 ``tl_settings_<ver>.json``，
   从别的目录启动就会读不到/写到别处。
2. **不写死 Together 的目录结构**：TGT 模组的目录布局改版过（``Resources/7z``
   与直接 ``7z`` 两种都出现过），所以这里按候选列表逐个探测，并且允许
   在设置里手动指定 ``seven_zip_path``。
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

#: 程序名（用于 %LOCALAPPDATA% 下的目录名）
APP_NAME = "TogetherLevelManager"

#: 设置文件名（不再把版本号写进文件名，升级不会丢配置）
SETTINGS_FILENAME = "tlm_settings.json"

#: 旧版本用过的设置文件名；找到就自动迁移
LEGACY_SETTINGS_PATTERNS = ("tl_settings_*.json",)


def app_dir() -> Path:
    """配置文件所在目录。

    优先级：环境变量 ``TLM_HOME`` > PyInstaller 打包后的 exe 目录 > 仓库根目录。
    """
    override = os.environ.get("TLM_HOME")
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):  # PyInstaller
        return Path(sys.executable).resolve().parent
    # tlm/paths.py -> tlm -> <root>
    return Path(__file__).resolve().parent.parent


def settings_path() -> Path:
    """设置文件的完整路径。"""
    return app_dir() / SETTINGS_FILENAME


def legacy_settings_files() -> list[Path]:
    """可能存在的旧版设置文件（按改动时间从新到旧）。"""
    found: list[Path] = []
    seen: set[Path] = set()
    for base in (app_dir(), Path.cwd()):
        try:
            for pattern in LEGACY_SETTINGS_PATTERNS:
                for p in sorted(base.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True):
                    rp = p.resolve()
                    if rp not in seen:
                        seen.add(rp)
                        found.append(rp)
        except OSError:
            continue
    return found


def together_dirs() -> list[Path]:
    """Together（TGT）模组可能的安装目录，按可信度排序。"""
    candidates: list[Path] = []
    for env in ("TLM_TOGETHER_DIR",):
        val = os.environ.get(env)
        if val:
            candidates.append(Path(val).expanduser())

    local = os.environ.get("LOCALAPPDATA")
    roaming = os.environ.get("APPDATA")
    if local:
        candidates.append(Path(local) / "Together")
    if roaming:
        candidates.append(Path(roaming) / "Together")
    # 便携版：7z 可能就在程序旁边
    candidates.append(app_dir() / "Resources" / "Together")
    candidates.append(app_dir())
    return candidates


def _seven_zip_candidates() -> list[Path]:
    """相对 Together 目录的 7z.exe 候选路径（布局改版过，按新→旧排列）。"""
    names = [
        Path("Resources") / "7z" / "7z.exe",
        Path("7z") / "7z.exe",
        Path("Resources") / "7z.exe",
        Path("7z.exe"),
    ]
    out: list[Path] = []
    for base in together_dirs():
        for name in names:
            out.append(base / name)
    return out


def probe_7z() -> list[tuple[str, bool]]:
    """探测过的路径及是否存在，用于报错时给出有用提示。"""
    return [(str(p), p.is_file()) for p in _seven_zip_candidates()]


def find_7z(explicit: str | None = None) -> str | None:
    """定位 7z 可执行文件。

    顺序：设置里手动指定 > 环境变量 ``TLM_7Z`` > Together 目录候选 > PATH。
    """
    for raw in (explicit, os.environ.get("TLM_7Z")):
        if raw:
            p = Path(raw).expanduser()
            if p.is_file():
                return str(p)

    for path in _seven_zip_candidates():
        if path.is_file():
            return str(path)

    for exe in ("7z", "7za"):
        found = shutil.which(exe)
        if found:
            return found
    return None
