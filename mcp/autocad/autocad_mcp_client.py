"""mcp.autocad.autocad_mcp_client · 封装第三方 AutoCAD MCP（Phase 13 §8）。

职责（仅传输层，禁止业务逻辑）：
- ``connect`` / ``disconnect``：建立 / 释放与 AutoCAD MCP 的连接。
- ``execute`` / ``send_command``：将一条 CAD Command 翻译为 MCP 工具调用并发送。
- ``receive_result``：取回上一次执行结果。
- ``health_check``：探测 AutoCAD MCP / AutoCAD 2026 可用性。

本模块不实现任何 AutoCAD 绘图语义（线/块/标注的几何计算属于 Drawing Agent /
Geometry Agent / CADAdapter），也不复制 ``puran-water/autocad-mcp`` 源码，仅描述其
接口与工具分组映射（见 ``capability_registry.json``）。

运行模式：
- 默认 ``transport=StdioMCPTransport``：对接真实 ``puran-water/autocad-mcp``（stdio）。
  离线环境未启动服务时 ``connect`` / ``health_check`` 返回不可用。
- 测试 / 离线验证可注入 ``SimulatedTransport``（参考实现，非真实 AutoCAD MCP），
  用于证明 Adapter → MCP → AutoCAD → DWG 的可验证闭环（Phase 13 §11 Test 3）。
"""

from __future__ import annotations

import json
import os
import secrets
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.cad_adapter.exceptions import (
    AutoCADConnectionError,
    AutoCADExecutionError,
    SchemaValidationError,
    UnsupportedCommandError,
)

_REGISTRY_PATH = Path(__file__).resolve().parent / "capability_registry.json"

# CAD command_type → (MCP 工具组, MCP 工具动作)
# 工具组名对齐 puran-water/autocad-mcp 暴露的能力分类；动作名为本系统语义映射。
COMMAND_TO_MCP_TOOL: Dict[str, tuple] = {
    "CREATE_LINE": ("entity", "draw_line"),
    "CREATE_POLYLINE": ("entity", "draw_polyline"),
    "CREATE_RECTANGLE": ("entity", "draw_polyline"),  # 经闭合 polyline 合成
    "CREATE_TEXT": ("annotation", "add_text"),
    "CREATE_DIMENSION": ("annotation", "add_dimension"),
    "CREATE_BLOCK": ("block", "create_insert"),
    "CREATE_LAYER": ("layer", "create_layer"),
    "SAVE_DWG": ("drawing", "save"),
    "OPEN_DWG": ("drawing", "open"),
    "READ_ENTITY": ("query", "get_entity"),
}


# ---------------------------------------------------------------------------
# Transport 抽象
# ---------------------------------------------------------------------------
class Transport(ABC):
    """MCP 传输层抽象（stdio / http / 参考 Simulated 均可实现）。"""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def send(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """发送一个 MCP 工具调用信封，返回结果 dict。"""

    @abstractmethod
    def health_check(self) -> bool: ...


class StdioMCPTransport(Transport):
    """对接真实 ``puran-water/autocad-mcp`` 的 stdio 传输（接口预留）。

    真实部署时由 ``AutoCADMCPClient(host/port)`` 或环境变量
    ``AUTOCAD_MCP_CMD``（启动命令）驱动；本环境未运行真实服务，
    ``connect`` / ``health_check`` 返回不可用，不臆造连接。
    """

    def __init__(self, command: Optional[str] = None) -> None:
        self._command = command or os.environ.get("AUTOCAD_MCP_CMD")
        self._connected = False

    def connect(self) -> None:
        if not self._command:
            raise AutoCADConnectionError(
                "未配置 AutoCAD MCP 启动命令（AUTOCAD_MCP_CMD）或服务地址；"
                "请先启动 puran-water/autocad-mcp。")
        # 真实实现应在此 spawn 子进程并建立 stdio JSON-RPC 管道；
        # 离线环境下不实际 spawn，直接判定不可用。
        raise AutoCADConnectionError(
            "真实 AutoCAD MCP 不可用（本环境未运行 AutoCAD 2026 / "
            "autocad-mcp 服务）。可注入 SimulatedTransport 完成离线闭环验证。")

    def disconnect(self) -> None:
        self._connected = False

    def send(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        raise AutoCADConnectionError("StdioMCPTransport 未连接")

    def health_check(self) -> bool:
        return False


class SimulatedTransport(Transport):
    """参考 / 测试用传输：模拟 ``puran-water/autocad-mcp`` 的最小行为与响应契约。

    说明：此为 InteriorDesignOS 自研的**测试替身**，不复制任何第三方 MCP 源码；
    仅用于在离线环境证明 ``Adapter → MCP → AutoCAD → DWG`` 的可验证闭环。
    真实部署应改用 ``StdioMCPTransport``。
    """

    def __init__(self) -> None:
        self._connected = False
        self._session: List[Dict[str, Any]] = []   # 已创建实体快照
        self._last: Optional[Dict[str, Any]] = None

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def health_check(self) -> bool:
        return self._connected

    @staticmethod
    def _new_handle() -> str:
        return secrets.token_hex(2).upper()  # 4 hex 字符，模拟 AutoCAD handle

    def send(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        if not self._connected:
            raise AutoCADConnectionError("SimulatedTransport 未连接")
        tool = envelope.get("name")
        args = envelope.get("arguments", {}) or {}
        if tool == "drawing.save":
            path = args.get("path")
            if not path:
                raise AutoCADExecutionError("SAVE_DWG 缺少 path")
            self._write_dwg(path)
            result = {"path": path, "status": "COMPLETED"}
        elif tool == "drawing.open":
            result = {"status": "COMPLETED"}
        elif tool == "query.get_entity":
            handle = args.get("handle")
            found = next((e for e in self._session if e.get("handle") == handle),
                         None)
            result = {"entity": found, "status": "COMPLETED" if found else "FAILED"}
        else:
            # 其余均为「创建类」工具：产出 handle 并记录会话
            handle = self._new_handle()
            ref = args.get("entity_id") or args.get("geometry_ref") \
                or args.get("name")
            self._session.append({
                "ref": ref, "type": tool, "handle": handle,
                "payload": args,
            })
            result = {"handle": handle, "status": "COMPLETED"}
        self._last = result
        return result

    def _write_dwg(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # 占位 DWG（非真实 DWG 二进制；仅用于闭环验证「DWG 存在」）
        p.write_text("INTERIORDESIGNOS-MOCK-DWG-1.0\n", encoding="utf-8")
        manifest = p.with_suffix(p.suffix + ".manifest.json")
        manifest.write_text(json.dumps({
            "format": "INTERIORDESIGNOS-MOCK-DWG-1.0",
            "entities": self._session,
        }, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# AutoCAD MCP 客户端
# ---------------------------------------------------------------------------
class AutoCADMCPClient:
    """封装第三方 AutoCAD MCP（纯传输层，无业务语义）。"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: float = 30.0,
        transport: Optional[Transport] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._transport = transport or StdioMCPTransport()
        self.connected = False
        self._last_result: Optional[Dict[str, Any]] = None

    # ---- 连接生命周期 ----------------------------------------------------
    def connect(self) -> None:
        self._transport.connect()
        self.connected = True

    def disconnect(self) -> None:
        try:
            self._transport.disconnect()
        finally:
            self.connected = False

    def health_check(self) -> bool:
        try:
            return bool(self._transport.health_check())
        except Exception:  # noqa: BLE001
            return False

    # ---- 命令执行 --------------------------------------------------------
    def _translate(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """CAD Command → MCP 工具调用信封。仅做协议翻译。"""
        ctype = command.get("command_type")
        if ctype not in COMMAND_TO_MCP_TOOL:
            raise UnsupportedCommandError(f"未注册 MCP 工具的命令: {ctype}")
        group, action = COMMAND_TO_MCP_TOOL[ctype]
        return {"name": f"{group}.{action}", "arguments": command.get("payload", {})}

    def execute(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """发送一条 CAD Command，返回规范化结果（含 handle / path / status）。"""
        if self._transport is None or not self.connected:
            raise AutoCADConnectionError("AutoCAD MCP 未连接")
        envelope = self._translate(command)
        try:
            raw = self._transport.send(envelope)
        except AutoCADConnectionError:
            self.connected = False
            raise
        except Exception as e:  # noqa: BLE001
            self.connected = False
            raise AutoCADExecutionError(f"AutoCAD 执行失败：{e}")
        self._last_result = raw
        return raw

    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """``execute`` 的语义别名（Phase 13 §8 接口要求）。"""
        return self.execute(command)

    def receive_result(self) -> Optional[Dict[str, Any]]:
        """取回上一次执行结果（流式场景可用）。"""
        return self._last_result


# ---------------------------------------------------------------------------
# 能力注册表
# ---------------------------------------------------------------------------
def load_capability_registry() -> Dict[str, Any]:
    """读取 ``capability_registry.json``（真实 AutoCAD MCP 能力）。"""
    if not _REGISTRY_PATH.exists():
        raise SchemaValidationError(
            f"能力注册表缺失: {_REGISTRY_PATH}")
    return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))


def supported_capabilities() -> List[str]:
    """返回注册表声明的 command_type 能力列表。"""
    return list(load_capability_registry().get("capabilities", []))


def has_capability(command_type: str) -> bool:
    """查询某 command_type 是否被真实 AutoCAD MCP 支持。"""
    return command_type in supported_capabilities()


__all__ = [
    "Transport", "StdioMCPTransport", "SimulatedTransport",
    "AutoCADMCPClient", "COMMAND_TO_MCP_TOOL",
    "load_capability_registry", "supported_capabilities", "has_capability",
]
