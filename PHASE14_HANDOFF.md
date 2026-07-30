# InteriorDesignOS · Phase 14 交接文档（Handoff）

> 整理时间：2026-07-28
> 整理人：前序 agent（调研 + 方案设计，未写代码）
> 目标读者：接手实现 Phase 14 的下一个 agent
> 配套阅读：`CHANGELOG.md`、`PROJECT_RULES.md`、`docs/architecture.md`、`PHASE13_COMPLETION_REPORT.md`

---

## 1. 背景与任务来源

- 工程 `InteriorDesignOS` 位于 `/Users/shijunteng/Desktop/图纸/InteriorDesignOS`，是一个**多智能体室内设计 CAD 自动化系统**，采用"逐 Phase 增量构建"的开发方式。
- 截至对话起点，系统已**完整完成 Phase 1 ~ Phase 13**（见 `CHANGELOG.md`），全量测试 **220 passed、lint 0 错误**（Phase 13 实测）。**不是 git 仓库**（无 `.git`）。
- 原始对话历史被省略，前序 agent 无法确定"未完成任务"具体是什么。经分析工程状态 + 与用户确认，用户明确选择方向：**新建 Phase 14**。
- 当前未做任何代码改动，本文档仅记录调研结论与一份可落地的 Phase 14 方案。

---

## 2. 项目结构速览（关键目录）

```
InteriorDesignOS/
├── agents/                 # AI 代理定义（parser/design/layout/geometry/drawing/validator/professional...）
├── cad/                    # 统一 CAD 后端抽象层（Phase 12 引入）
│   ├── adapter/            # base(CADAdapter 抽象) / mock_adapter / autocad_adapter / registry
│   ├── capability/         # backends.json + capability.py（后端能力系统）
│   ├── command/            # DrawingCommand / CommandQueue
│   ├── mock/  cad_validator.py  base/  autocad/
│   └── mcp/                # ⚠️ 遗留的 cad.mcp 客户端（见 §3.2）
├── mcp/                    # Phase 13 引入的"唯一允许调用 AutoCAD MCP"的适配层
│   ├── cad_adapter/        # CADAdapter(编排) / command_mapper / entity_mapper / dwg_bridge / exceptions
│   └── autocad/            # autocad_mcp_client.py（StdioMCPTransport / SimulatedTransport）
├── runtime/                # 编排/调度/流水线（pipeline/cad_export.py 含 Round-Trip）
├── models/                 # 各模型 dataclass（generated.py 含 GeneratedModel）
├── schemas/                # JSON Schema 契约（含 cad_tool.schema.json）
├── tests/                  # cad/ cad_adapter/ runtime/ professional/ ...
├── CHANGELOG.md / ROADMAP.md / PROJECT_RULES.md / PHASE13_COMPLETION_REPORT.md
```

---

## 3. 关键调研发现（Phase 14 必须解决的分歧）

### 3.1 两套同名的 `CADAdapter` 并存

| 类 | 文件 | 角色 | 接口形态 |
|----|------|------|----------|
| `cad.adapter.base.CADAdapter` | `cad/adapter/base.py` | **后端接口**（Phase 12） | 抽象方法：`create_document / create_layer / create_entity / create_dimension / save_dwg / load_dwg / close` |
| `mcp.cad_adapter.cad_adapter.CADAdapter` | `mcp/cad_adapter/cad_adapter.py` | **执行编排器**（Phase 13） | `run(commands, dwg_path)` / `execute(dm, dwg_path, geometry_model, project_id)`，内部持有 `AutoCADMCPClient` |

两者重名但职责不同：前者是"后端"抽象，后者是"把模型翻译成命令并驱动 MCP"的编排器。这正是 Phase 13 报告 §9 建议 #3 要"收敛"的对象。

### 3.2 两个不兼容的 `AutoCADMCPClient`（核心分歧）

| 文件 | 调用风格 | 被谁使用 |
|------|----------|----------|
| `mcp/autocad/autocad_mcp_client.py`（**Phase 13 规范实现**） | `execute(command_dict)`，command 含 `command_type`+`payload`；内部 `COMMAND_TO_MCP_TOOL` 把 `command_type` 翻译为 `group.action`；含 `SimulatedTransport` + `StdioMCPTransport` | `mcp.cad_adapter.CADAdapter` |
| `cad/mcp/autocad_mcp_client.py`（**Phase 12 遗留**） | `execute(tool, arguments)`（`cad.*` 风格） | `cad/adapter/autocad_adapter.py`（`cad.adapter.AutoCADAdapter`） |

二者 `execute` 签名与协议完全不同，互不兼容。Phase 12 的 `AutoCADAdapter` 调用的是 `(tool, args)` 风格，而 Phase 13 的 `CommandMapper` 产出的是 `CAD Tool Command Contract` dict（恰好匹配 `mcp.autocad` 客户端）。**Phase 14 应让 AutoCAD 执行统一收敛到 `mcp.autocad.AutoCADMCPClient`。**

### 3.3 Phase 12 已有完整 mock 闭环，但 Phase 13 被隔离在外

- `runtime/pipeline/cad_export.py` 已实现**完整的 mock 后端 Round-Trip**：
  - `translate_drawing_model(dm)` → Phase 12 中性实体（WALL→polyline / DOOR,WINDOW→line / FURNITURE→block / annotation→text，携带 `tag`+`role`）
  - `export_drawing_to_dwg` → `MockCADAdapter` 写出 `*.dwg`（Mock 容器，可完整回读）
  - `read_dwg_to_generated_model` → 回读 → `GeneratedModel`
  - `round_trip_validate(generated, layout_model)` → 比对 LayoutModel（房间/墙/门窗数量、坐标误差、尺寸误差）
  - `run_dwg_round_trip(...)` → 一站式闭环
- **Phase 13 的 `mcp.cad_adapter.CADAdapter.run()` 只产出 `generated_model`（经 `ReferenceDWGBridge` 读 manifest），从不把 DWG 回读、也从不调用 `round_trip_validate`**。即 Phase 13 报告 §8 第 4 条明确写明的"与 Phase 12 Round-Trip 隔离，未合并"。
- 因此 **Phase 14 最高价值项 = 把 Phase 13 的执行编排接入 Phase 12 的回读 + 校验闭环**（同时满足 `PROJECT_RULES.md` §19 强制的 DWG Round-trip Validation）。

### 3.4 Mock 后端回读可用性确认

`MockCADAdapter`（`cad/adapter/mock_adapter.py`）：
- `load_dwg(path)` 返回 `{"path", "backend", "layers", "entities", "dimensions", ...}`，其中 `entities` 是原样存储的中性实体（含 `role`、`tag`、`type`、`layer`、坐标等），`dimensions` 含 `tag`。
- `supports(type)` 走 capability 注册表（`cad/capability/backends.json` 中 mock 支持 line/polyline/circle/arc/text/block/dimension/layer/save_dwg/read_dwg）。
- ⇒ 用 `backend="mock"` 走 Phase 14 新编排器，可真回读并喂给 `round_trip_validate`，在离线环境即可验证闭环 PASS。

---

## 4. 适用约束（务必遵守 `PROJECT_RULES.md` 最高约束）

实现 Phase 14 时**不可违反**：

1. §19 DWG Round-trip Validation **强制**：DWG 生成后必须重新打开→解析→`GeneratedModel`→比对 `LayoutModel`→校验，未通过不得 `DELIVERED`。
2. §7.1 所有 AutoCAD 自动化写操作必须经 MCP；**`mcp.cad_adapter` 是唯一允许调用 AutoCAD MCP 的模块**（Agent 层禁止直接调用）。
3. **禁止修改 `LayoutModel` SSOT**（只能读取比对）。
4. **禁止修改 Schema Contract**（`cad_tool.schema.json`、各 Model Schema 字段不变；新增只在既有 `GeneratedModel` 字段内组合使用）。
5. **禁止新增设计 Agent**（Layout/Geometry/Drawing 行为不变）。
6. **DWG 不作为 Agent 间内部通信格式**（内部仍用中性实体 dict / CAD Tool Command Contract；DWG 仅作最终产物 + Round-Trip 回读）。
7. 失败时诚实报错、不静默 fallback（`cad_export.py` / `autocad_mcp_client.py` 已遵循）。

---

## 5. Phase 14 方案设计：统一 CAD 后端收敛与 Round-Trip 闭环

> 命名建议：**Phase 14：Unified CAD Backend Convergence & Round-Trip Closure**

原则：**以"增量、低侵入、离线可测"为主**，不删除既有代码以免破坏 220 测试；把 Phase 13 编排器升级为"统一 CAD 执行门面"，可驱动 mock/autocad 两种引擎，并接入 Phase 12 的回读+校验闭环。

### 交付物 1 — `mcp/cad_adapter/backend_selector.py`（新增）

定义编排器可驱动的"画布引擎"抽象与解析：
- `class CanvasEngine`（Protocol/ABC）：`backend_name`、`supports(cap)`、`create_document`、`create_layer`、`create_entity`、`create_dimension`、`save_dwg`、`load_dwg`、`close`。
- `MockCanvasEngine`：包裹 `cad.adapter.MockCADAdapter`（真实可回读）。
- `AutoCADCanvasEngine`：包裹 `mcp.autocad.AutoCADMCPClient`；把中性实体经 `CommandMapper` 转 `CAD Tool Command Contract` 后执行；`load_dwg` 走 `READ_ENTITY`（离线不可用则降级读 manifest）。
- `resolve_canvas_engine(backend="auto", **opts)`：按能力选择 + 自动降级（autocad 不可用时降级 mock，沿用 `cad.capability.select_backend` 语义）。

### 交付物 2 — 扩展 `mcp/cad_adapter/cad_adapter.py` 的 `CADAdapter`

- 当前签名：`CADAdapter(client, entity_mapper=None, dwg_bridge=None, mapper=None)`，方法 `build_commands / run(commands, dwg_path, project_id) / execute(dm, dwg_path, geometry_model, project_id) / _ensure_save_dwg / _track`。**必须保持该 API 向后兼容**（现有 `tests/cad_adapter/test_autocad_connection.py` 直接 `CADAdapter(client)` + `adapter.run(...)`）。
- 新增参数：`backend: str = "auto"` 与可选 `engine`（注入便于测试）。
- `run()` 内部分支：
  - `backend == "mock"`（或 auto 解析到 mock）→ 用 `translate_drawing_model(dm)` 得到中性实体，直接驱动 `MockCanvasEngine`（`create_document`→`create_layer`→`create_entity`→`create_dimension`→`save_dwg(dwg_path)`），构建 `generated_model`（含 `cad_backend`/`entity_mapper`/`counts`/`layers`/`entities`/`dimensions`/`source`），实体带 `role`+`tag`。
  - `backend == "autocad"` → 走既有 `_execute_command` 路径（经 `AutoCADMCPClient`）。
- 让 `CADAdapter` 成为**唯一 CAD 执行门面**，内部 `AutoCADCanvasEngine` 仍属于 `mcp.cad_adapter`，满足 §7.1。

### 交付物 3 — `mcp/cad_adapter/dwg_bridge.py` 新增 `BackendDWGBridge`

- 新增 `BackendDWGBridge(DWGBridge)`：经给定 `engine.load_dwg(path)` 重新读取 DWG，返回完整 `GeneratedModel` dict（`layers/entities/dimensions/counts`）——**取代单纯依赖 `ReferenceDWGBridge` 的 manifest 技巧**，并对 mock 实现"真回读"。
- 保留 `DWGBridge` 抽象与 `ReferenceDWGBridge`（向后兼容，标注 deprecated）。

### 交付物 4 — `runtime/pipeline/cad_export.py` 新增 `run_unified_round_trip`

```python
def run_unified_round_trip(drawing_model, geometry_model, layout_model,
                           dwg_path, project_id="project", backend="mock") -> dict:
    # 1) Phase 14 统一编排器产出 DWG + GeneratedModel
    adapter = CADAdapter(geometry_model, drawing_model, project_id, backend=backend)
    gen = adapter.run()                       # 或 execute(...)
    # 2) 经 BackendDWGBridge 真回读 DWG
    bridge = BackendDWGBridge(adapter.engine) # 或按 backend 解析
    regen = bridge.read(dwg_path)
    # 3) 接入 Phase 12 的 round_trip_validate（比对 LayoutModel）
    validation = round_trip_validate(regen, layout_model)
    return {"export_generated": gen, "readback_generated": regen, "validation": validation}
```
- 这关闭了 Phase 13 报告 §8.4 明写的"隔离"缺口，并满足 `PROJECT_RULES.md` §19。

### 交付物 5 — CI 分离

- 新增 `tests/cad_adapter/conftest.py`：定义 `AUTOCAD_MCP_CMD` 探测与 `pytest.mark.autocad_required`。
- 改造 `tests/cad_adapter/test_autocad_connection.py`：真实连接用例用 `skipif(not autocad_available)` 守护；Simulated 路径始终运行，离线 CI 不误报。

### 交付物 6 — 收敛/弃用遗留客户端

- 在 `cad/mcp/autocad_mcp_client.py` 顶部加弃用说明，指向规范实现 `mcp.autocad.AutoCADMCPClient`（**保留文件不删**，以免破坏 `cad.adapter.autocad_adapter` 及其测试）。
- `mcp/cad_adapter/__init__.py` 导出 `make_cad_adapter(...)` 工厂（统一入口）。

### 交付物 7 — 文档

- 新增 `PHASE14_COMPLETION_REPORT.md`（参照 Phase 13 报告结构：目标/新增/修改/架构/验证/限制/下一阶段）。
- 更新 `CHANGELOG.md`（追加 `[Unreleased]` 下的 Phase 14 条目）。
- 更新 `ROADMAP.md`（勾选已被本 Phase 推进的项，如"AutoCAD MCP 连接器（双向）""DWG 往返校验"）。

---

## 6. 实施步骤（建议顺序）

1. 先读（务必先重读，避免凭记忆误改）：
   - `mcp/cad_adapter/cad_adapter.py`、`dwg_bridge.py`、`command_mapper.py`、`entity_mapper.py`、`exceptions.py`
   - `cad/adapter/{base,mock_adapter,autocad_adapter,registry}.py`
   - `cad/capability/{capability.py,backends.json}`
   - `runtime/pipeline/cad_export.py`、`models/generated.py`
2. 实现 `backend_selector.py`（画布引擎抽象 + Mock/AutoCAD 引擎 + 解析降级）。
3. 扩展 `cad_adapter.py`：增加 `backend`/`engine` 参数与 mock 驱动分支；保持既有 `client`/`run`/`execute` API 不变。
4. 实现 `dwg_bridge.py` 的 `BackendDWGBridge`。
5. 在 `cad_export.py` 增加 `run_unified_round_trip`。
6. 加测试 `tests/cad_adapter/test_backend_selector.py` 与 `tests/cad_adapter/test_unified_round_trip.py`（离线 mock 闭环断言 `validation["passed"] is True`）。
7. 改造 `tests/cad_adapter/conftest.py` + `test_autocad_connection.py` 加 CI 守护。
8. 标记 `cad/mcp/autocad_mcp_client.py` 弃用，补 `make_cad_adapter` 工厂。
9. 跑全量测试：`python3 -m pytest tests/ -q`（目标：≥234 passed，0 回归，lint 0）。
10. 写 `PHASE14_COMPLETION_REPORT.md`，更新 `CHANGELOG.md` / `ROADMAP.md`。

---

## 7. 测试与验收

- 既有 220 测试（`tests/cad`、`tests/cad_adapter`、`tests/runtime` 等）必须全部保持通过（不要改坏 `run`/`execute` 既有语义）。
- 新增 `test_unified_round_trip`：用 `schemas/examples/DrawingModel.example.json` + `GeometryModel.example.json` + 对应 `LayoutModel.example.json`，经 `backend="mock"` 跑 `run_unified_round_trip`，断言：
  - `export_generated["counts"]` 合理（参照 Phase 13 报告：line 5 / block 1 / dimension 2 / layer 4 / text 1）；
  - `readback_generated` 来自 `load_dwg` 真回读；
  - `validation["passed"] is True`（房间/墙/门窗数量、坐标误差 ≤1mm、尺寸误差 ≤1mm，与 `round_trip_validate` 默认容差一致）。
- 真实 AutoCAD 连接用例离线 `skip`（CI 不误报），SimulatedTransport 路径仍验证。

---

## 8. 开放问题 / 注意事项（接手前确认）

1. **Phase 13 `cad_adapter.py` 当前 `run()` 的 `generated_model` 结构**：建议直接复用 `runtime.pipeline.cad_export.translate_drawing_model` 产出中性实体（在 `run()` 内延迟 import 以避免循环依赖）。**改动前务必重读该文件确认现状**（前文已贴出当前完整内容，但重读一次最稳妥）。
2. **`round_trip_validate` 的房间计数依赖 `DIM-{room_id}` 标注**：确保 DrawingModel 的 dimensions 中带 `tag` 形如 `DIM-<room_id>`，否则 `room_count` 校验会 fail。可在测试样例里用 `examples/e2e` 既有产物验证。
3. **不要删除 `cad.mcp` 遗留客户端**：仅加弃用注释，保证 `cad.adapter.AutoCADAdapter` 现有测试不崩。
4. **真实 AutoCAD 环境本机没有**（无 AutoCAD 2026 / puran-water/autocad-mcp），autocad 引擎路径只能离线靠 `SimulatedTransport` 验证"执行通路"，真回读（READ_ENTITY）保持接口预留、诚实报错。

---

## 9. 关键文件索引（绝对路径）

| 用途 | 路径 |
|------|------|
| 编排器（待扩展） | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/mcp/cad_adapter/cad_adapter.py` |
| 命令映射 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/mcp/cad_adapter/command_mapper.py` |
| 实体映射 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/mcp/cad_adapter/entity_mapper.py` |
| DWG 桥接（待加 BackendDWGBridge） | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/mcp/cad_adapter/dwg_bridge.py` |
| AutoCAD MCP 客户端（规范） | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/mcp/autocad/autocad_mcp_client.py` |
| 能力登记 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/mcp/autocad/capability_registry.json` |
| 后端接口（Phase 12） | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/cad/adapter/base.py` |
| Mock 后端 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/cad/adapter/mock_adapter.py` |
| 遗留 AutoCAD 适配器 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/cad/adapter/autocad_adapter.py` |
| 后端注册表 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/cad/adapter/registry.py` |
| 能力系统 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/cad/capability/{capability.py,backends.json}` |
| 遗留客户端（标记弃用） | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/cad/mcp/autocad_mcp_client.py` |
| Round-Trip 闭环（待加 unified） | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/runtime/pipeline/cad_export.py` |
| GeneratedModel | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/models/generated.py` |
| 最高约束 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/PROJECT_RULES.md` |
| 变更日志 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/CHANGELOG.md` |
| 路线图 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/ROADMAP.md` |
| Phase 13 报告 | `/Users/shijunteng/Desktop/图纸/InteriorDesignOS/PHASE13_COMPLETION_REPORT.md` |
| 既有测试 | `tests/cad_adapter/{test_geometry_commands,test_drawing_commands,test_autocad_connection}.py`、`tests/cad/{test_adapter,test_autocad_adapter,test_dwg_roundtrip,test_mock_backend,...}.py` |
| 示例模型 | `schemas/examples/{DrawingModel,GeometryModel,LayoutModel}.example.json` |

---

## 10. 一句话总结给下一个 agent

> 把 Phase 13 的 `mcp.cad_adapter.CADAdapter` 升级为**统一 CAD 执行门面**：既能驱动 `MockCADAdapter`（真实可回读），也能驱动 `mcp.autocad.AutoCADMCPClient`（经 `CommandMapper`）；并让它的产物接入 Phase 12 已有的 `BackendDWGBridge`/`round_trip_validate`，闭合"DrawingModel → DWG → 回读 → GeneratedModel → 比对 LayoutModel"这条 Phase 13 报告里明确写"未合并"的链路。全程遵守 `PROJECT_RULES.md`（§7.1 / §19 等），不破坏既有 220 测试、不删遗留代码、不修改 Schema 与 LayoutModel。
