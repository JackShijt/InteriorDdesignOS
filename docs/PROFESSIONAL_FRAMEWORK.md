# PROFESSIONAL_FRAMEWORK

> **Professional Deepening Framework 规范（Phase 5 / 5.1）** · v1.1
>
> 遵守 [`PROJECT_RULES.md`](PROJECT_RULES.md) v1.1、[`architecture.md`](architecture.md) v1.2、
> [`WORKFLOW.md`](../WORKFLOW.md) v1.0、[`schema-design.md`](schema-design.md) v1.0。
>
> 本阶段禁止：AutoCAD MCP、生成 DWG、调用外部 AI。全部 Professional Agent 为 **Mock Logic**。

---

## 1. 概述

Professional Deepening Framework 为 8 个专业设计 Agent 建立统一运行模式：

| 专业 | Agent | Model | 领域字段 |
| --- | --- | --- | --- |
| 电气 | `ElectricalAgent` | `ElectricalModel` | switches / sockets / lights / circuits / panel |
| 给排水 | `PlumbingAgent` | `PlumbingModel` | water_supply / drain / equipment |
| 照明 | `LightingAgent` | `LightingModel` | fixtures / groups / controls |
| 吊顶 | `CeilingAgent` | `CeilingModel` | ceiling_regions / levels / materials |
| 地面 | `FlooringAgent` | `FlooringModel` | areas / materials / patterns |
| 暖通 | `HVACAgent` | `HVACModel` | air_supply / return_air / equipment |
| 施工 | `ConstructionAgent` | `ConstructionModel` | notes / details / specifications |
| 家具 | `FurnitureAgent` | `FurnitureModel` | movable / fixed / clearance |

硬约束（Phase 5 §一）：

- Professional Agent **只能读取** LayoutModel（SSOT）；可以读取 DesignSpec。
- **不允许**修改 LayoutModel / DesignSpec（基类返回深拷贝以强制只读）。
- **不允许**直接操作 DWG。
- 全部输出 ProfessionalModel，由 ProfessionalValidator 统一校验。

目录结构（Phase 5.1 后）：

```text
core/                            # 架构基础层（最底层，禁止反向依赖）
├── context/agent_context.py     # AgentContext / Result / BaseAgent / make_metadata
├── artifact/artifact_manager.py # ArtifactManager（save/load/exists/archive/delete）
└── logging.py                   # NullLogger / JsonFileLogger / build_logger

models/
└── base/model_converter.py      # ModelConverter（dataclass ↔ dict/json）

professional/
├── __init__.py                  # PROFESSIONAL_DISCIPLINES + Agent 工厂
├── validator.py                 # ProfessionalValidator（聚合校验）
├── base/
│   ├── professional_agent.py    # BaseProfessionalAgent（流程层）
│   ├── professional_model.py    # BaseProfessionalModel（公共 dataclass）
│   └── rule_engine.py           # BaseRuleEngine（专业规则层基类）
├── electrical/  ├── plumbing/  ├── lighting/  ├── ceiling/
├── flooring/    ├── hvac/      ├── construction/  └── furniture/
    └── <discipline>_agent.py / <discipline>_rules.py / <discipline>_model.py
```

---

## 1.1 Dependency Rules（Phase 5.1）

分层依赖，**只允许自上而下**，禁止反向依赖：

```text
Runtime
    |
Orchestrator
    |
Agent
    |
RuleEngine
    |
Model
```

底层共享包：`core/`（context / artifact / logging）与 `models/`（converter），
可被任意上层依赖，但**禁止** import 任何上层包。

| 包 | 允许依赖 | 禁止依赖 |
| --- | --- | --- |
| `runtime/` | orchestrator、professional、core、models、schemas | — |
| `agents/orchestrator/` | core、models、schemas | runtime |
| `professional/`（Agent / RuleEngine / Model） | core、models、schemas | **runtime、orchestrator、agents** |
| `core/`、`models/` | 标准库 / 三方库 | **一切上层包** |

行为约束（Phase 5.1）：

1. Professional Agent 不知道 Runtime 实现，也不知道 Orchestrator。
2. Agent 只接受 `AgentContext`（`run(context)` 单参数），全部输入来自
   `context.inputs / parameters / workspace`。
3. Agent 不直接读写 Workspace 文件；所有输出经 `ArtifactManager`：
   `Agent → ProfessionalModel(dataclass) → ArtifactManager → workspace/`。
4. Agent 不自行管理 Artifact 生命周期（版本归档 / 删除由 ArtifactManager 负责）。
5. JSON 序列化统一经 `ModelConverter` / `to_json()` / `from_json()`，
   禁止 Agent 手写 `json.dump`。
6. 专业规则全部在 `<discipline>_rules.py::<D>RuleEngine`；Agent 只负责流程
   （`validate_input → generate_model → publish_result`）。

以上规则由 `tests/architecture/` 静态 + 行为测试强制（见 §8）。

---

## 2. 专业 Agent 生命周期

所有 Agent 继承 `BaseProfessionalAgent`，公共生命周期由基类统一提供，
子类**只实现** `_build_model()`（Mock 对象生成），禁止重复实现公共逻辑：

所有 Agent 继承 `BaseProfessionalAgent`，子类只声明 `discipline` +
`rule_engine_class`；专业规则在对应 `<D>RuleEngine.build()` 中（Phase 5.1 §9）：

```text
run(context: AgentContext)
 ├─ 1. load_layout(context)      读取 LayoutModel（深拷贝，只读）
 │      inputs.layout → inputs.layout_path → parameters.layout_path
 │      → input_refs(*.json) → <context.workspace>/layout_model.json
 ├─ 2. load_design_spec(context) 读取 DesignSpec（可选，深拷贝，只读）
 ├─ 3. validate_input()          校验 metadata/version/rooms/walls 与 model_version
 ├─ 4. generate_model()          RuleEngine.build() → 强类型 dataclass
 │      → 注入 metadata/版本/quality → Schema 校验（失败禁止落盘）
 └─ 5. publish_result()          ProfessionalModel → ArtifactManager
        → <project>/professional/<discipline>_model.json（旧版本自动归档）
        ↓
Result(success, output_model, messages, quality)   # 异常一律转失败 Result
```

```text
ElectricalAgent          ←  流程（validate / generate / publish）
        |
ElectricalRuleEngine     ←  专业规则（纯函数，无 IO）
        |
ElectricalModel          ←  强类型 dataclass（to_json / from_json）
```

失败语义：任何一步异常均被捕获并转为 `Result(success=False)`（框架安全，
PROJECT_RULES 错误处理约定），不向 Runtime 抛出。

---

## 3. ProfessionalModel

公共 Schema：`schemas/professional/professional_model.schema.json`
（`additionalProperties: false`，禁止 CAD / Geometry / DWG / Entity / Layer 字段）。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `metadata` | object | 统一元数据（canonical: `core/metadata.schema.json`） |
| `layout_model_version` | string | 所基于的 LayoutModel 版本（版本链追溯） |
| `discipline` | enum | ELECTRICAL / PLUMBING / LIGHTING / CEILING / FLOORING / HVAC / CONSTRUCTION / FURNITURE |
| `objects` | array | 专业对象（`id` + `category` + `room_id?` + `spec?`） |
| `constraints` | array | 规范性约束（`type` + `description`，非几何约束） |
| `quality` | object | 质量评分（canonical: `validation/quality.schema.json`） |

实现层：`BaseProfessionalModel`（dataclass）声明公共字段与序列化；各专业 dataclass
仅声明领域集合字段（如 `switches`），由 `COLLECTION_FIELDS` / `SINGLE_FIELDS`
自动汇总为统一 `objects`（每项附 `category`）。

示例：`schemas/examples/ProfessionalModel.example.json`。

---

## 4. 并行执行机制（Parallel Fan-out / Fan-in）

```text
LayoutModel
   ↓ Fan-out：Orchestrator.run_professional_stage(task_ids)
   ↓          （ThreadPoolExecutor，经 Dispatcher 调度各 Agent）
Electrical ∥ Plumbing ∥ Lighting ∥ Ceiling ∥ Flooring ∥ HVAC ∥ Construction ∥ Furniture
   ↓ Fan-in：等待全部完成（as_completed 聚合）
ProfessionalValidator（聚合校验）
   ↓
Export（清单 + 报告 + 检查点）
```

- **执行器**：`runtime/parallel.py::ParallelStageRunner`
  - `run_once(jobs)`：Fan-out 全部作业并等待全部完成（Fan-in）。
  - `retry_failed(jobs, outcome)`：**只重跑失败作业**，成功者不重新执行。
  - 作业内异常一律转失败 `Result`（部分失败不影响其它 Agent）。
- **调度**：`Orchestrator.run_professional_stage()` 经 `Dispatcher.execute(task_id,
  save_checkpoint=False)` 执行任务；检查点在 Fan-in 后由 Pipeline 统一保存，
  避免多个任务并发写同一 stage 检查点文件。
- **入口**：
  - CLI：`python main.py professional <project_id> [--layout <json>] [--disciplines a,b,c]`
  - 演示：`python examples/professional/mock_workflow.py`（Electrical / Lighting / HVAC / Furniture）
  - API：`Pipeline.run_professional(layout_path, disciplines)`
- **重试**：失败任务复位为 `READY` 后单独重跑（次数 = `max_retry - 1`）；
  已 `COMPLETED` 的任务在重入时直接跳过。

---

## 5. Validator 聚合流程

`professional/validator.py::ProfessionalValidator.validate_all(models, layout)`：

1. **Schema 合法**：逐一校验 `professional_model.schema.json`（含 `$ref` Registry）。
2. **Quality 合法**：`confidence∈[0,1]`、`quality_score∈[0,100]`、`validation_passed=True`。
3. **版本一致**：所有模型 `metadata.schema_version` 一致。
4. **LayoutVersion 一致**：所有模型 `layout_model_version` 相同，且等于
   `LayoutModel.version.model_version`。

输出聚合报告并写入 `<project>/professional_validation_report.json`：

```json
{
  "passed": true,
  "checked": 8,
  "disciplines": ["CEILING", "..."],
  "errors": {},
  "version_errors": [],
  "layout_model_versions": { "ELECTRICAL": "v1" },
  "timestamp": "..."
}
```

报告 `passed=false` 时项目转 `FAILED`，禁止 Export。

---

## 6. 版本一致性要求

- 每个 ProfessionalModel 必须声明 `layout_model_version`（Agent 输入版本声明，
  architecture.md §14）。
- 同一次专业深化的全部模型必须基于**同一** LayoutModel 版本；不一致即聚合校验失败。
- LayoutModel 是唯一可信源（SSOT）：专业模型只能引用（`room_id` / `layout_ref`），
  禁止复制或回写布局数据。
- LayoutModel 升版（v1 → v2）后，专业模型必须基于新版本重新生成，旧模型仅作历史留存。

---

## 7. 产物与检查点

| 产物 | 路径 |
| --- | --- |
| 专业模型 | `<project>/professional/<discipline>_model.json` |
| 聚合校验报告 | `<project>/professional_validation_report.json` |
| Export 清单 | `<project>/professional_export_manifest.json` |
| 阶段检查点 | `<project>/checkpoint_professional_v1.json` |

---

## 8. 测试

`tests/architecture/`（Phase 5.1 架构测试）：

- `test_import_dependency.py`：professional/core/models 禁止 import
  runtime / orchestrator / agents（AST 静态扫描）。
- `test_artifact.py`：professional 内无直接文件写入；Agent 输出确实经
  `ArtifactManager.save`；save/load/exists/archive/delete 生命周期与版本归档。
- `test_context.py`：`AgentContext` 必备字段；所有 Agent `run(context)` 单参数
  签名；输入可完全经 Context 内联传递；`context.workspace` 生效。

`tests/professional/`（35 项）：

- `test_professional_agent.py`：基类生命周期、8 Agent 可运行、SSOT 只读、输入校验。
- `test_professional_model.py`：8 个模型领域字段与序列化契约。
- `test_parallel_execution.py`：Fan-out/Fan-in、真并行、部分失败、只重跑失败作业。
- `test_professional_validator.py`：聚合校验、Quality 校验。
- `test_version_check.py`：LayoutVersion / schema_version 一致性。
- `test_schema_check.py`：Schema 必填字段、八专业枚举、CAD 字段禁入。
- `test_professional_pipeline.py`：端到端 Mock Workflow 与失败重跑隔离。

---

## 9. 与 Phase 6 的边界

本阶段全部为 Mock Logic：不做真实专业设计计算，不生成 DWG，不调用 AutoCAD MCP。
Phase 6（CAD Integration & AutoCAD MCP）将在本框架之上接入真实 CAD 链路。
