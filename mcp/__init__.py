"""mcp · 外部工具连接器（architecture.md §3 L4 工具层）。

本包仅承载「与外部 MCP / 工具 的接口描述与执行适配」，不复制任何第三方
AutoCAD MCP / Blender / 3dsMax / Photoshop 源码（PROJECT_RULES §15、Phase 13 约束）。

Phase 13 新增：
- ``mcp/cad_adapter/``  ：InteriorDesignOS Model → CAD Command → AutoCAD MCP 的执行适配层
  （唯一允许调用 AutoCAD MCP 的模块）。
- ``mcp/autocad/``      ：对第三方 ``puran-water/autocad-mcp`` 的接口封装与能力注册（只读描述）。
- ``mcp/schemas/``      ：CAD Tool Command Contract（``cad_tool.schema.json``）。
"""
