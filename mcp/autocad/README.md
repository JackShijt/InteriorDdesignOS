# mcp/autocad — 外部 AutoCAD MCP 接口描述

> **本目录仅为第三方 `puran-water/autocad-mcp` 的接口描述与封装，不复制其源码。**
> Phase 13 不开发 AutoCAD MCP、不开发 AutoCAD 插件（见 Phase 13 最高约束）。

## 角色定位

- **InteriorDesignOS = 控制端**，AutoCAD 2026 = 执行端。
- `mcp/autocad/` 是 InteriorDesignOS 与第三方 AutoCAD MCP 之间的**薄封装层**：
  - `autocad_mcp_client.py`：封装 MCP 通信（`connect` / `execute` / `health_check` /
    `send_command` / `receive_result`），**仅做协议翻译，不含业务逻辑**。
  - `capability_registry.json`：记录 AutoCAD MCP 实际暴露的能力（据真实工具组映射）。

## 接入方式

`puran-water/autocad-mcp` 通过 **stdio + MCP JSON-RPC** 驱动 AutoCAD（LT 2024+ / 2026），
支持自然语言经 AutoLISP 生成与执行。其内部暴露约 18 个工具组
（`drawing` / `entity` / `layer` / `block` / `annotation` / `query` / `export` …）。

本系统的 `AutoCADMCPClient` 默认使用 `StdioMCPTransport`，真实部署时由
环境变量 `AUTOCAD_MCP_CMD` 或 `host/port` 指向已启动的 MCP 服务。

## 能力（当前登记）

见 `capability_registry.json`：CREATE_LINE / CREATE_POLYLINE / CREATE_RECTANGLE /
CREATE_TEXT / CREATE_DIMENSION / CREATE_BLOCK / CREATE_LAYER / OPEN_DWG /
SAVE_DWG / READ_ENTITY。

## 不在本目录

- ❌ AutoCAD MCP 源码
- ❌ AutoCAD 插件 / AutoLISP
- ❌ DWG 解析内核（属于 `mcp/cad_adapter/dwg_bridge.py`）

## 参考链接（外部）

- https://github.com/puran-water/autocad-mcp
