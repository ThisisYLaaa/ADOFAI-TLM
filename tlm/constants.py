"""全局常量与默认配置。

原来集中在 ``Init_Settings.py``，现在作为包内的唯一常量来源。
"""

from __future__ import annotations

VERSION = "1.1.0"

#: ttkbootstrap 主题名
THEMENAME = "darkly"

#: 单次鼠标滚轮滚动的行数
WHEEL_SCROLL_UNIT = 3

#: 解压 / 扫描关卡时使用的线程数
LOAD_THREAD = 20

#: 认定为关卡压缩包的扩展名
ARCHIVE_EXTS = (".zip", ".rar", ".7z")

#: 关卡文件的扩展名
LEVEL_EXT = ".adofai"

#: 没有读到时占位显示的文字
UNKNOWN = "unknown"

#: 设置文件默认内容；新增的键会自动合并进旧配置文件
DEFAULT_SETTINGS: dict = {
    "zip_folder": "",
    "save_folder": "",
    "unzip_cache_folder": "",
    "auto_load": False,
    "types": ["Init"],
    # 留空 = 自动探测 Together 自带的 7z.exe（见 tlm.paths.find_7z）
    "seven_zip_path": "",
}
