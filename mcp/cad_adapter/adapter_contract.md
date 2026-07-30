# CAD Adapter Contract（适配层契约）

> Phase 13 §4 / §6 / §7 / §10 的形式化说明。本契约约束 `mcp/cad_adapter/` 与上下游的
> 交互边界，确保 Agent 层不触碰外部 CAD 执行端。

---

## 1. 唯一调用权

```
Drawing Agent ──X 禁止 ──> AutoCAD MCP
Geometry Agent ──X 禁止 ──> DWG
CAD Adapter   ──OK 允许 ──> AutoCAD MCP ──> AutoCAD 2026
```

- `CADAdapter` 是 `mcp/cad_adapter/` 中唯一持有 `AutoCADMCPClient` 并触达外部的模块。
- `command_mapper` / `entity_mapper` / `dwg_bridge` 均为纯函数 / 纯数据，不发起网络调用。

---

## 2. Model → Command 契约

输入：`DrawingModel.entities` / `GeometryModel.lines|polygons|dimensions`
输出：符合 `mcp/schemas/cad_tool.schema.json` 的 CAD Command 列表

映射（严格、无设计判定）：

| 来源 | command_type |
|------|--------------|
| WALL / DOOR / WINDOW | CREATE_LINE |
| FURNITURE / BLOCK | CREATE_BLOCK |
| DIMENSION | CREATE_DIMENSION |
| ANNOTATION | CREATE_TEXT |
| LAYER | CREATE_LAYER |
| Geometry.line | CREATE_LINE |
| Geometry.polygon | CREATE_POLYLINE（closed） |
| Geometry.dimension | CREATE_DIMENSION |

`command_mapper` 不修改 Geometry / Layout，不判断合理性。坐标仅在提供
`geometry_model` 时**查表**注入 payload（只读引用）。

---

## 3. Entity 追踪契约

`entity_mapper` 维护 `entity_id ↔ autocad_handle`：

- `register(entity_id, handle)`：回读 / 修改 / 验证时用。
- 同 `entity_id` 不可静默重映射（防回读错位）。
- `entries()` 输出供 `GeneratedModel` 携带，实现 Model 级可追溯。

---

## 4. DWG → GeneratedModel 契约

`DWGBridge.read` / `generate_model` 为 Phase 13 接口：

- `ReferenceDWGBridge`：从 DWG manifest 副本身建 `GeneratedModel`（离线验证用，
  **不解析真实 DWG 二进制**）。
- 真实部署应替换为对接 `puran-water/autocad-mcp` 的 `READ_ENTITY` / DWG 解析能力。

---

## 5. 通信格式

- 内部通信一律为 CAD Tool Command Contract（JSON），**禁止**以 DWG 作为内部格式。
- `status` 复用系统状态机：`PENDING / RUNNING / COMPLETED / FAILED`。

---

## 6. 禁止项（Phase 13）

❌ 自动设计户型 ❌ AI 判断空间 ❌ 修改 LayoutModel ❌ 自动优化家具
❌ 写 AutoCAD 插件 ❌ 替代 puran-water/autocad-mcp ❌ 实现完整 DWG 内核
