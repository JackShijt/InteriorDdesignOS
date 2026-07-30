"""mcp.autocad · 第三方 AutoCAD MCP 接口描述（Phase 13，只读，不复制源码）。"""

from mcp.autocad.autocad_mcp_client import (
    AutoCADMCPClient,
    SimulatedTransport,
    StdioMCPTransport,
    Transport,
    has_capability,
    load_capability_registry,
    supported_capabilities,
)

__all__ = [
    "AutoCADMCPClient", "Transport", "StdioMCPTransport", "SimulatedTransport",
    "load_capability_registry", "supported_capabilities", "has_capability",
]
