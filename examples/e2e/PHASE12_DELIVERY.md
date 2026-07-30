# Phase12 CAD Backend Integration Complete

日期：2026-07-27
标记：**Phase12 CAD Backend Integration Complete**

验收链路（已跑通）：

```
LayoutModel → GeometryModel → DrawingModel → CAD Adapter → DWG
    → GeneratedModel → Validation（Compare LayoutModel）
```

启动命令（不变）：

```
python scripts/run_project.py examples/e2e/demo001.json
```

最终日志（实测）：

```
CAD Backend: Mock
DWG Generated: .../workspace/projects/demo001/cad/demo001.dwg
Round Trip Validation: PASSED (coord_err=0.005mm, dim_err=0.04mm)
Project Delivered
```

---

## 1. 修改 / 新增文件列表

### 新增（Phase 12.1 CAD Adapter Layer）
| 文件 | 说明 |
|---|---|
| `cad/adapter/base.py` | `CADAdapter` 统一接口（create_document/create_layer/create_entity/create_dimension/save_dwg/load_dwg/close）+ 异常体系 |
| `cad/adapter/mock_adapter.py` | `MockCADAdapter`：确定性 Mock 后端，DWG 用 `MOCK-DWG-1.0` 容器格式落盘，可完整回读 |
| `cad/adapter/autocad_adapter.py` | `AutoCADAdapter`：统一接口 → AutoCAD MCP 工具调用（本阶段无真实连接，失败即降级） |
| `cad/adapter/registry.py` | 后端注册表：`create_adapter` / `resolve_adapter`（能力检测 + 可用性探测 + 自动降级） |
| `cad/adapter/__init__.py` | 包导出 |

### 新增（Phase 12.2 Capability System）
| 文件 | 说明 |
|---|---|
| `cad/capability/backends.json` | 后端能力声明（mock：10 项；autocad：line/polyline/block/dimension/layer/save_dwg/read_dwg） |
| `cad/capability/capability.py` | 能力检测 `has_capability`、后端切换 `select_backend`、降级处理 `missing_capabilities` |
| `cad/capability/__init__.py` | 包导出 |

### 新增（Phase 12.3 AutoCAD MCP 接口预留）
| 文件 | 说明 |
|---|---|
| `cad/mcp/autocad_mcp_client.py` | `AutoCADMCPClient`：connect / send_command / execute / query / disconnect（复用 Phase 7 `MCPClient` 传输层；不要求真实连接） |

### 新增（Phase 12.4 / 12.5 Pipeline & Round Trip）
| 文件 | 说明 |
|---|---|
| `runtime/pipeline/cad_export.py` | `translate_drawing_model`（DrawingModel→后端中性实体）、`export_drawing_to_dwg`、`read_dwg_to_generated_model`、`round_trip_validate`、`run_dwg_round_trip` |

### 新增（Phase 12.6 测试）
| 文件 | 说明 |
|---|---|
| `tests/cad/test_adapter.py` | 接口一致性 / 注册表 / 能力系统 / 降级（14 用例） |
| `tests/cad/test_mock_backend.py` | Mock 后端行为 + DrawingModel 生成 CAD 实体 + DWG 导出（12 用例） |
| `tests/cad/test_dwg_roundtrip.py` | DWG Round-Trip 闭环 + 失配检测 + autocad 降级闭环（5 用例） |

### 修改
| 文件 | 说明 |
|---|---|
| `models/generated.py` | **完善 GeneratedModel**：新增 `dwg_path/layers/entities/dimensions/counts`（全部有默认值，向后兼容） |
| `runtime/pipeline/e2e_pipeline.py` | DRAWING 阶段接入 `_run_dwg_round_trip`：DrawingModel→Adapter→DWG→回读→GeneratedModel→RoundTripReport；state/checkpoint/finalize 增加 dwg/round_trip 字段 |
| `runtime/pipeline/stage_builders.py` | Mock 门/窗补充 `start/end` 线段派生字段（仅 Mock 构造器，不涉及 LayoutModel SSOT 结构定义） |
| `cad/mcp/__init__.py` | 导出 `AutoCADMCPClient` |
| `scripts/run_project.py` | 增加最终日志：CAD Backend / DWG Generated / Round Trip Validation / Project Delivered |
| `CHANGELOG.md` | Phase 12 记录 |

---

## 2. CAD Adapter 设计说明

```
DrawingAgent / Pipeline（不知道具体 CAD 软件）
        │  只依赖统一接口
        ▼
cad.adapter.resolve_adapter(preferred, required_capabilities)
        │  1) capability 层选后端（select_backend，能力不足→降级）
        │  2) 可用性探测（AutoCAD MCP 未连接→降级 mock）
        ▼
CADAdapter（抽象基类）
 ├── MockCADAdapter     backend="mock"    DWG=Mock 容器格式（JSON in .dwg）
 └── AutoCADAdapter     backend="autocad" 经 AutoCADMCPClient → MCP 工具
```

要点：
- **Agent 禁止直接调用 CAD API**：唯一入口为 `cad.adapter`；AutoCAD API 细节被封装在 `AutoCADAdapter` + `AutoCADMCPClient` 内。
- **后端中性实体**：`translate_drawing_model` 把 DrawingModel 翻译为 line/polyline/block/text/dimension 中性结构，携带 `tag`（源 entity_id）与 `role`（wall/door/window/…），供回读对齐。
- **能力驱动降级**：后端不支持的实体类型（如 autocad 未声明 `text`/`circle`）导出时跳过并计入 `skipped`；整体能力不足则由 `select_backend` 切换后端。
- **扩展方式**：新后端 = 实现 `CADAdapter` + `register_adapter(name, factory)` + 在 `backends.json` 声明能力，上层零改动。

## 3. 测试结果

```
tests/cad（新增 31 用例）  31 passed
全量回归                  206 passed（Phase 11 为 178，+28 净增*）
lint                      0 错误
```

\* tests/cad 原有 Phase 7 适配器测试保持通过。

## 4. DWG 生成日志（实测摘录）

```
Running: drawing
  DWG Generated: .../demo001/cad/demo001.dwg  (backend=mock)
  layers=6, entities=80+, dimensions=9, skipped=[]
Completed: GeneratedModel
```

完整日志：`examples/e2e/phase12_e2e_run.log`
DWG 文件：`examples/e2e/workspace/projects/demo001/cad/demo001.dwg`

## 5. Round Trip 验证结果（实测）

`examples/e2e/workspace/projects/demo001/validation/reports/RoundTripReport.json`：

| 检查项 | 期望 | 实际 | 结果 |
|---|---|---|---|
| room_count | 9 | 9 | PASS |
| wall_count | 36 | 36 | PASS |
| door_count | 9 | 9 | PASS |
| window_count | 9 | 9 | PASS |
| coordinate_error | ≤1.0mm | 0.005mm（54 元素） | PASS |
| dimension_error | ≤1.0mm | 0.04mm（9 标注） | PASS |

**passed = true**，比对基准：LayoutModel。

---

## 约束遵守

- ❌ 未修改 LayoutModel 结构（SSOT 不变）
- ❌ 未修改 Schema Contract
- ❌ 未新增设计 Agent
- ❌ 未开发 UI
- ❌ 未实现装修算法
- ✅ AutoCAD 仅接口预留（Phase 12.3），无真实连接；不可用时自动降级 Mock
