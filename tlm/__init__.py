"""Together Level Manager —— 基于 ttkbootstrap 的 ADOFAI 关卡批量管理器。

对外只暴露版本号等轻量信息：这里不导入任何 GUI 依赖，
因此 `import tlm` 可以在无显示环境（CI / 服务器）里安全使用。
"""

from __future__ import annotations

from .constants import VERSION

__version__ = VERSION

__all__ = ["__version__", "VERSION"]
