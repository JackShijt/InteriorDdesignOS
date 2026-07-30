# mcp/cad_adapter — CAD 执行适配层（Phase 13）

> InteriorDesignOS Model 层 → CAD Adapter → AutoCAD MCP → AutoCAD 2026 → DWG → GeneratedModel
> 的可验证闭环。

## 模块职责

| 文件 | 职责 |
|------|------|
| `cad_adapter.py` | **唯一允许调用 AutoCAD MCP 的模块**；编排 Model→Command→执行→DWG→GeneratedModel。 |
| `command_mapper.py` | DrawingModel / GeometryModel → CAD Command（纯结构翻译，不改 Geometry/Layout）。 |
| `entity_mapper.py` | `entity_id ↔ autocad_handle` 双向追踪（回读/修改/验证）。 |
| `dwg_bridge.py` | DWG → GeneratedModel（Phase 13 仅接口 + 参考实现）。 |
| `exceptions.py` | CAD Adapter 执行链路异常体系。 |
| `adapter_contract.md` | 适配层契约说明。 |

## 调用边界（最高约束）

- ✅ Drawing Agent / Geometry Agent **禁止**直接调用 AutoCAD MCP。
- ✅ 仅 `CADAdapter` 可经 `AutoCADMCPClient` 与外部通信。
- ✅ DWG **不**作为内部通信格式；内部一律以 CAD Tool Command Contract（`mcp/schemas/cad_tool.schema.json`）通信。

## 使用

```python
from mcp.cad_adapter import CADAdapter
from mcp.autocad.autocad_mcp_client import AutoCADMCPClient, SimulatedTransport

client = AutoCADMCPClient(transport=SimulatedTransport())  # 离线参考模式
adapter = CADAdapter(client)
report = adapter.execute(drawing_model, "out/demo.dwg", geometry_model=geometry_model)
print(report["dwg_path"], report["generated_model"]["counts"])
```

真实部署将 `transport=SimulatedTransport()` 替换为默认（`StdioMCPTransport`），并启动
`puran-water/autocad-mcp`。
