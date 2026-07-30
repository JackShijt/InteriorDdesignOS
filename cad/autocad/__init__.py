"""cad/autocad（Phase 7）— AutoCAD 后端适配器（经 MCP）。

CAD Framework 不直接 import 本模块；通过 cad/__init__.py 的插件注册表
``CAD_BACKENDS`` 加载，从而满足「CAD 后端插件化 / 框架不感知 AutoCAD」。
"""
from __future__ import annotations

from .autocad_adapter import AutoCADAdapter

__all__ = ["AutoCADAdapter"]
