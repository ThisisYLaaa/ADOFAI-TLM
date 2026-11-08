"""worker 线程 → 主线程 的安全桥。

Tkinter 控件只能在主线程碰。旧代码在 ``ThreadPoolExecutor`` 里直接
``self.progress['value'] += 1``、``status_var.set(...)``，属于典型的
跨线程操作 Tkinter，轻则界面不刷新，重则整程序卡死。

这里的做法是：worker 只往 ``queue.Queue`` 里丢消息，主线程用 ``after()``
周期性排空队列再改控件——这是 Tkinter 官方推荐的模式。
"""

from __future__ import annotations

import queue
import tkinter as tk
from typing import Any, Callable


class UiBridge:
    """把任意线程的 UI 更新请求排队，交给主线程执行。"""

    #: 每次排空最多处理多少条消息，避免一次回调卡太久
    DRAIN_BATCH = 200

    def __init__(self, root: tk.Misc, sink: Callable[[str, Any], None], interval_ms: int = 60) -> None:
        self._root = root
        self._sink = sink
        self._interval_ms = interval_ms
        self._queue: "queue.Queue[tuple[str, Any]]" = queue.Queue()
        self._alive = True
        self._schedule()

    # ------------------------------------------------------------------ 生产者
    def status(self, message: str) -> None:
        self._queue.put(("status", message))

    def progress(self, value: int, maximum: int) -> None:
        self._queue.put(("progress", (value, maximum)))

    def call(self, func: Callable[..., None], *args: Any) -> None:
        """把一个无参/带参调用丢回主线程执行（用于弹窗、刷新表格等）。"""
        self._queue.put(("call", (func, args)))

    # ------------------------------------------------------------------ 消费者
    def _schedule(self) -> None:
        if not self._alive:
            return
        try:
            self._root.after(self._interval_ms, self._drain)
        except tk.TclError:  # 窗口已销毁
            self._alive = False

    def _drain(self) -> None:
        for _ in range(self.DRAIN_BATCH):
            try:
                kind, payload = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                self._sink(kind, payload)
            except tk.TclError:
                self._alive = False
                return
            except Exception:  # noqa: BLE001 - UI 更新失败不该拖垮桥
                continue
        self._schedule()

    def close(self) -> None:
        self._alive = False
