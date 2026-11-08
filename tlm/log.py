"""日志。

相比旧实现修掉的问题：
* 旧代码在 formatter 里对 ``record.msg`` 做 ``.replace("/", "\\\\")``，
  会把所有路径的反斜杠翻倍，而且 msg 不是 str 时直接崩；
* 旧代码先用带颜色的 levelname 去查颜色表，导致消息颜色永远取不到；
* 无处理器重复添加的判断保留，避免多次 import 刷屏。
"""

from __future__ import annotations

import logging

try:  # colorama 是可选依赖：没有它也能正常打日志
    from colorama import Back, Fore, Style
    from colorama import init as _colorama_init

    _colorama_init(autoreset=True)
except Exception:  # pragma: no cover - 环境缺依赖时的降级路径
    class _Ansi:
        def __getattr__(self, _name: str) -> str:
            return ""

    Fore = Back = _Ansi()  # type: ignore[assignment]
    Style = _Ansi()  # type: ignore[assignment]


class IconColorFormatter(logging.Formatter):
    """给日志加图标与颜色；可通过 ``miao`` 关掉语气后缀。"""

    ICONS: dict[str, str] = {
        "DEBUG": "🔍",
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "💥",
    }
    COLORS: dict[str, str] = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.WHITE,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Back.WHITE + Style.BRIGHT,
    }

    def __init__(self, fmt: str | None = None, datefmt: str | None = None, miao: bool = True) -> None:
        super().__init__(fmt, datefmt)
        self.miao = miao

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        message = record.getMessage()  # 先按 %-args 展开，之后不再依赖 args
        icon = self.ICONS.get(level, "📝")
        color = self.COLORS.get(level, "")

        record.msg = message
        record.args = ()

        if color:
            record.levelname = f"{color}{icon} {level}{Style.RESET_ALL}"
            suffix = "喵" if (self.miao and "喵" not in message) else ""
            record.msg = f"{color}{message}{suffix}{Style.RESET_ALL}"
        else:
            record.levelname = f"{icon} {level}"
            if self.miao and "喵" not in message:
                record.msg = f"{message}喵"

        return super().format(record)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """取得带统一格式的 logger（同名 logger 只装配一次）。"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            IconColorFormatter(
                "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.propagate = False
    return logger
