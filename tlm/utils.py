"""通用工具：文件/压缩包操作与 HTML 文本清洗。"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess

from .constants import ARCHIVE_EXTS
from .log import get_logger
from .paths import find_7z, probe_7z

logger = get_logger(__name__)

#: 隐藏子进程窗口（仅 Windows 有意义）
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class FileUtils:
    """文件操作工具类。"""

    # ---------------------------------------------------------------- 7z 相关
    @staticmethod
    def get_7z_path(explicit: str | None = None) -> str | None:
        """获取 7z.exe 路径；找不到返回 ``None``。"""
        return find_7z(explicit)

    @staticmethod
    def describe_7z_lookup() -> str:
        """把探测过的路径拼成一段可读提示，用于报错。"""
        lines = ["7z.exe 未找到。已探测："]
        lines += [f"  {'✓' if ok else '✗'} {path}" for path, ok in probe_7z()]
        lines.append("可在「设置 → 7z 路径」里手动指定，或设置环境变量 TLM_7Z。")
        return "\n".join(lines)

    @staticmethod
    def _require_7z(explicit: str | None) -> str:
        seven_zip = FileUtils.get_7z_path(explicit)
        if not seven_zip:
            logger.error(FileUtils.describe_7z_lookup())
            raise FileNotFoundError("未找到 7z 可执行文件（Together 自带或系统安装均可）")
        return seven_zip

    @staticmethod
    def _run_7z(command: list[str]) -> bool:
        try:
            subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=_NO_WINDOW,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or b""
            message = stderr.decode("gbk", errors="ignore") if stderr else str(exc)
            logger.error(f"解压错误: {message}")
            raise

    # ---------------------------------------------------------------- 文件名
    @staticmethod
    def sanitize_filename(name: str) -> str:
        """移除文件名中的非法字符。"""
        if not name:
            return "未知关卡"
        cleaned = re.sub(r'[<>:"/\\|?*]', "", name).strip()
        return cleaned or "未知关卡"

    # ---------------------------------------------------------------- 解压
    @staticmethod
    def extract_full_archive(archive_path: str, output_dir: str, seven_zip: str | None = None) -> bool:
        """完整解压压缩包到 ``output_dir``。"""
        exe = FileUtils._require_7z(seven_zip)
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"解压: {archive_path} -> {output_dir}")
        return FileUtils._run_7z([exe, "x", f"-o{output_dir}", "-y", archive_path])

    @staticmethod
    def extract_adofai_only(archive_path: str, output_dir: str, seven_zip: str | None = None) -> bool:
        """只把谱面与音频解到 ``output_dir``（扁平化，不保留目录结构）。"""
        exe = FileUtils._require_7z(seven_zip)
        os.makedirs(output_dir, exist_ok=True)
        return FileUtils._run_7z(
            [exe, "e", f"-o{output_dir}", "-y", archive_path, "-r", "*.adofai", "*.ogg", "*.wav"]
        )

    @staticmethod
    def list_archives(folder: str) -> list[str]:
        """列出目录下（不含子目录）的压缩包文件名。"""
        if not folder or not os.path.isdir(folder):
            return []
        return [
            name
            for name in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, name)) and name.lower().endswith(ARCHIVE_EXTS)
        ]

    # ---------------------------------------------------------------- 目录
    @staticmethod
    def clear_directory(directory: str) -> None:
        """清空目录下的所有内容（保留目录本身）。"""
        if not directory or not os.path.exists(directory):
            return
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)


class HtmlUtils:
    """HTML 清洗工具类（谱面元数据里常混有 Unity 富文本标签）。"""

    _TAG_RE = re.compile(r"<[^>]+>")

    @staticmethod
    def clean_html_tags(text: object) -> object:
        if not isinstance(text, str):
            return text
        text = html.unescape(text)
        text = re.sub(r"<color=[^>]*>", "", text)
        text = re.sub(r"<size=[^>]*>", "", text)
        text = re.sub(r"</?(color|size|b|i|u|br)[^>]*>", "", text, flags=re.IGNORECASE)
        text = HtmlUtils._TAG_RE.sub("", text)
        return text.strip()
