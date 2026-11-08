"""兼容旧入口：``python UI.py`` 仍然可用（等价于 ``python main.py``）。

v1.1.0 起代码已迁到 :mod:`tlm` 包，本文件只是转发，避免旧快捷方式失效。
"""

from __future__ import annotations

import warnings

from tlm.__main__ import main

warnings.warn(
    "`python UI.py` 是旧入口，请改用 `python main.py` 或 `python -m tlm`",
    DeprecationWarning,
    stacklevel=1,
)

if __name__ == "__main__":
    main()
