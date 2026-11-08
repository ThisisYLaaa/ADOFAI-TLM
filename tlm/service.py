"""关卡扫描 / 解压服务（不含任何 GUI 依赖）。

旧实现把进度条与状态栏的更新直接写在 ``ThreadPoolExecutor`` 的 worker 里，
而 Tkinter 控件只能在主线程操作——这是偶发卡死/花屏的根源。这里改成回调：

    manager = LevelManager(zip_folder=..., cache_folder=..., on_status=..., on_progress=...)

回调在 worker 线程里被调用，**由调用方负责切回主线程**（GUI 侧用队列轮询）。
"""

from __future__ import annotations

import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .constants import LEVEL_EXT, LOAD_THREAD, UNKNOWN
from .log import get_logger
from .models import Level
from .utils import FileUtils

logger = get_logger(__name__)

StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[int, int], None]


def _noop_status(_message: str) -> None:  # pragma: no cover - 默认占位
    return None


def _noop_progress(_value: int, _maximum: int) -> None:  # pragma: no cover
    return None


class LevelManager:
    """把「压缩包目录 → 缓存目录（含 .adofai）→ Level 列表」串起来。"""

    def __init__(
        self,
        zip_folder: str,
        cache_folder: str,
        seven_zip: str | None = None,
        max_workers: int = LOAD_THREAD,
        on_status: StatusCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self.zip_folder = zip_folder or ""
        self.cache_folder = cache_folder or ""
        self.seven_zip = seven_zip or None
        self.max_workers = max(1, int(max_workers))
        self.on_status = on_status or _noop_status
        self.on_progress = on_progress or _noop_progress
        self.levels: list[Level] = []
        self._progress_lock = threading.Lock()
        self._level_lock = threading.Lock()

    # ------------------------------------------------------------------ 入口
    def load_levels(self) -> list[Level]:
        """处理压缩包 → 扫描缓存目录 → 返回关卡列表。"""
        self.levels = []
        self.process_archives()
        self.scan_levels()
        if not self.levels:
            self.on_status("没有发现任何关卡")
        else:
            self.on_status(f"加载完成，共 {len(self.levels)} 个关卡")
        return self.levels

    # ------------------------------------------------------------------ 解压
    def process_archives(self) -> None:
        """把 zip/rar/7z 里的谱面与音频解到缓存目录。"""
        archives = FileUtils.list_archives(self.zip_folder)
        if not archives:
            logger.info("没有需要处理的压缩包文件")
            self.on_status("没有需要处理的压缩包文件")
            return

        logger.info(f"发现 {len(archives)} 个压缩包文件")
        self.on_status(f"正在处理 {len(archives)} 个压缩包...")
        self._run_pool(archives, self._process_single_archive, total=len(archives))

    def _process_single_archive(self, file_name: str) -> None:
        file_path = os.path.join(self.zip_folder, file_name)
        base_name = os.path.splitext(file_name)[0]
        output_dir = os.path.join(self.cache_folder, base_name)
        try:
            if self._has_level_file(output_dir):
                logger.info(f"跳过已处理文件: {file_name}")
                self.on_status(f"跳过已处理: {file_name}")
                return

            os.makedirs(output_dir, exist_ok=True)
            shutil.copy2(file_path, output_dir)
            FileUtils.extract_adofai_only(file_path, output_dir, seven_zip=self.seven_zip)
            logger.info(f"成功处理: {file_name} -> {output_dir}")
            self.on_status(f"成功处理: {file_name}")
        except Exception as exc:  # noqa: BLE001 - 单个压缩包失败不应中断整批
            logger.error(f"处理失败 {file_name}: {exc}")
            self.on_status(f"处理失败 {file_name}: {exc}")

    @staticmethod
    def _has_level_file(folder: str) -> bool:
        if not os.path.isdir(folder):
            return False
        return any(name.lower().endswith(LEVEL_EXT) for name in os.listdir(folder))

    # ------------------------------------------------------------------ 扫描
    def scan_levels(self) -> None:
        """递归扫描缓存目录下的每个子目录，每个目录取第一个 ``.adofai``。"""
        if not self.cache_folder or not os.path.isdir(self.cache_folder):
            logger.warning(f"缓存目录不存在，跳过扫描: {self.cache_folder!r}")
            self.on_status("缓存目录不存在，请先在设置里指定")
            return

        folders: list[str] = []
        for root_dir, subdirs, _files in os.walk(self.cache_folder):
            if root_dir != self.cache_folder:
                folders.append(root_dir)
            # 不进入隐藏目录（如 .git / .cache）
            subdirs[:] = [d for d in subdirs if not d.startswith(".")]

        if not folders:
            logger.info("在缓存路径下未找到任何关卡文件夹")
            self.on_status("在缓存路径下未找到任何关卡文件夹")
            return

        logger.info(f"发现 {len(folders)} 个关卡文件夹")
        self.on_status(f"发现 {len(folders)} 个关卡文件夹")
        self._run_pool(folders, self._scan_single_folder, total=len(folders))

    def _scan_single_folder(self, folder_path: str) -> None:
        try:
            level_files = [
                name
                for name in os.listdir(folder_path)
                if name.lower().endswith(LEVEL_EXT)
                and os.path.isfile(os.path.join(folder_path, name))
            ]
            if not level_files:
                return
            level_files.sort()
            file_path = os.path.join(folder_path, level_files[0])
            level = Level(file_path)
            with self._level_lock:
                self.levels.append(level)
            logger.info(f"成功加载关卡: {file_path}")
            self.on_status(f"成功加载: {level.song or UNKNOWN}")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"加载关卡失败 {folder_path}: {exc}")
            self.on_status(f"加载关卡失败 {folder_path}: {exc}")

    # ------------------------------------------------------------------ 线程池
    def _run_pool(self, items: list[str], worker, total: int) -> None:
        """通用线程池执行器：统一进度上报，避免各处重复写计数逻辑。"""
        self.on_progress(0, total)
        done = 0

        def _wrapped(item: str) -> None:
            nonlocal done
            try:
                worker(item)
            finally:
                with self._progress_lock:
                    done += 1
                    current = done
                self.on_progress(current, total)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            list(executor.map(_wrapped, items))
