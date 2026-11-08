"""关卡数据模型。"""

from __future__ import annotations

import os
import time

from .constants import ARCHIVE_EXTS, LEVEL_EXT, UNKNOWN
from .log import get_logger
from .parser import Parser
from .utils import FileUtils, HtmlUtils

logger = get_logger(__name__)

#: 从音频文件名补歌曲名时认的扩展名
_AUDIO_EXTS = (".ogg", ".wav")


class Level:
    """一个关卡：解析后的谱面数据 + 展示用的元信息。"""

    def __init__(self, file_path: str) -> None:
        self.dir_path: str = os.path.dirname(file_path)
        self.file_path: str = file_path
        self.data: dict = Parser(file_path)()

        settings = self.data.get("settings") or {}
        song = settings.get("song") or ""
        artist = settings.get("artist") or ""
        author = settings.get("author") or ""

        self.archive_path, self.date = self._detect_archive()

        if not song:
            song = self._song_from_audio_files()

        self.song: str = str(HtmlUtils.clean_html_tags(song)) or UNKNOWN
        self.artist: str = str(HtmlUtils.clean_html_tags(artist)) or UNKNOWN
        self.author: str = str(HtmlUtils.clean_html_tags(author)) or UNKNOWN
        self.date: str = self.date or UNKNOWN

        self.size: int = len(self.data.get("angleData") or [])

    # ------------------------------------------------------------------ 辅助
    def _detect_archive(self) -> tuple[str, str]:
        """在关卡目录里找压缩包，用它的修改时间当关卡日期。

        旧实现在「目录里没有压缩包」时会漏掉 ``self.date`` 的赋值，
        紧接着 ``self.date or 'unknown'`` 直接抛 ``AttributeError``——
        这是本次重构修掉的真实崩溃点。
        """
        try:
            entries = os.listdir(self.dir_path)
        except OSError as exc:
            logger.error(f"无法读取关卡目录 {self.dir_path}: {exc}")
            return "", ""

        for name in entries:
            if name.lower().endswith(ARCHIVE_EXTS):
                path = os.path.join(self.dir_path, name)
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    continue
                return path, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        return "", ""

    def _song_from_audio_files(self) -> str:
        """没有写歌名时，用目录里的音频文件名兜底。"""
        try:
            audio = [f for f in os.listdir(self.dir_path) if f.lower().endswith(_AUDIO_EXTS)]
        except OSError:
            return ""
        if not audio:
            return ""
        if len(audio) > 1:
            return str([os.path.splitext(f)[0] for f in audio])
        return os.path.splitext(audio[0])[0]

    # ------------------------------------------------------------------ 输出
    def get_display_values(self) -> tuple[str, str, str, str]:
        """返回树形视图四列的值：(歌曲, 艺术家, 作者, 日期)。"""
        return self.song, self.artist, self.author, self.date

    def save(self, save_path: str, seven_zip: str | None = None) -> bool:
        """把整个压缩包解压到 ``save_path`` 下的关卡目录。

        :param save_path: 目标根目录（通常是 ``<保存路径>/<类型>``）
        :param seven_zip: 可选的 7z.exe 路径覆盖
        """
        try:
            folder_name = FileUtils.sanitize_filename(f"{self.song}_{self.artist}_{self.author}")
            save_folder = os.path.join(save_path, folder_name)
            os.makedirs(save_folder, exist_ok=True)
            if not self.archive_path:
                logger.error(f"关卡目录里没有可解压的压缩包: {self.dir_path}")
                return False
            FileUtils.extract_full_archive(self.archive_path, save_folder, seven_zip=seven_zip)
            logger.info(f"已保存: {save_folder}")
            return True
        except Exception as exc:  # noqa: BLE001 - 保存失败不该中断整批导出
            logger.error(f"保存关卡失败: {exc}")
            return False

    def __repr__(self) -> str:
        return f"Level(song={self.song!r}, size={self.size}, date={self.date!r})"

    @staticmethod
    def is_level_file(path: str) -> bool:
        return path.lower().endswith(LEVEL_EXT)
