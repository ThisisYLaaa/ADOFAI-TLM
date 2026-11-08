"""``python -m tlm`` 入口。"""

from __future__ import annotations

import multiprocessing


def main() -> None:
    """启动 GUI。``freeze_support`` 让 PyInstaller 打包后不会无限拉起子进程。"""
    multiprocessing.freeze_support()
    from .ui.main_window import UI  # 延迟导入：无显示环境不该在 import 阶段崩

    UI().mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
