# CHANGELOG

## [Unreleased]

### Added
- 初始项目结构创建

## [2026-07-27] Phase 13：CAD Execution Adapter Integration（COMPLETE）

> 建立 InteriorDesignOS（控制端）与外部 `puran-water/autocad-mcp`（执行端）之间的
> **CAD 执行适配层** `mcp/cad_adapter/`。链路：DrawingModel/GeometryModel → CAD Adapter
> → AutoCAD MCP → AutoCAD 2026 → DWG → GeneratedModel。遵守 PROJECT_RULES / ARCHITECTURE /
> WORKFLOW / SCHEMA_DESIGN；未修改 LayoutModel SSOT、未修改 Schema Contract、未新增设计
> Agent、未让 Drawing/Geometry Agent 直接调用 AutoCAD、DWG 不作为内部通信格式。提交标记：
> **Phase13 CAD Execution Adapter Integration Complete**。

### Added
- `mcp/cad_adapter/`（Phase 13 §4/§6/§7/§10）：`cad_adapter.py`（**唯一允许调用 AutoCAD
  MCP 的模块**，编排 Model→Command→执行→DWG→GeneratedModel）；`command_mapper.py`
  （DrawingModel/GeometryModel → CAD Command，纯结构翻译，不改 Geometry/Layout）；
  `entity_mapper.py`（`entity_id ↔ autocad_handle` 双向追踪）；`dwg_bridge.py`
  （DWG→GeneratedModel 接口 + 参考实现 `ReferenceDWGBridge`，不解析真实 DWG 二进制）；
  `exceptions.py`（执行链路异常体系）；`adapter_contract.md` / `README.md`（契约与说明）。
- `mcp/autocad/`（§8/§9）：`autocad_mcp_client.py`（封装第三方 AutoCAD MCP，仅
  `connect/execute/health_check/send_command/receive_result` + Transport 抽象
  `StdioMCPTransport`(真实)/`SimulatedTransport`(离线参考，非真实 MCP 源码)）；
  `capability_registry.json`（据真实 MCP 工具组登记能力，不假设不存在的能力）；
  `README.md`（外部工具接口描述，不复制源码）。
- `mcp/schemas/cad_tool.schema.json`（§5）：CAD Tool Command Contract，定义
  `command_id/command_type/source_model/source_version/payload/status` 与
  `command_type` 初始 10 类、`status` 复用系统状态机（PENDING/RUNNING/COMPLETED/FAILED）。
- `tests/cad_adapter/`（§11）：Test 1（GeometryModel→CAD Commands 数量一致，4 用例）、
  Test 2（DrawingModel→Command List，WALL→CREATE_LINE / FURNITURE→CREATE_BLOCK /
  DIM→CREATE_DIMENSION / 坐标解析，6 用例）、Test 3（Adapter→MCP→AutoCAD 连接与测试线
  + DWG 存在 + 端到端闭环，4 用例）。合计 14 个新用例。

### Verified
- 全量测试 **220 passed**（206 → 220），lint 0 错误。
- `python3 -m pytest tests/cad_adapter -q` → 14 passed：几何/图元映射数量一致、命令类型
  映射正确、坐标解析、真实连接离线不可用时诚实报错、SimulatedTransport 注入下创建测试线
  并验证 DWG 文件存在、DrawingModel+GeometryModel 端到端生成 GeneratedModel（line 5 /
  block 1 / dimension 2 / layer 4 / text 1）且 entity 追踪到 handle。

## [2026-07-27] Phase 12：CAD Backend Integration（COMPLETE）

> 将系统从「CAD 抽象层 + Mock 输出」升级为「统一 CAD Adapter 驱动 + DWG 闭环验证」。验收链路：LayoutModel → GeometryModel → DrawingModel → CAD Adapter → DWG → GeneratedModel → Validation（Compare LayoutModel）。遵守 PROJECT_RULES / ARCHITECTURE / WORKFLOW / Schema Contract；未修改 LayoutModel SSOT、未修改 Schema Contract、未新增设计 Agent、未开发 UI、未实现装修算法。提交标记：**Phase12 CAD Backend Integration Complete**。

### Added
- `cad/adapter/`（§12.1 CAD Adapter Layer）：`base.py` 定义统一接口 `CADAdapter`（create_document / create_layer / create_entity / create_dimension / save_dwg / load_dwg / close）与异常体系；`mock_adapter.py`（确定性 Mock 后端，DWG 以 MOCK-DWG-1.0 容器格式落盘并可完整回读）；`autocad_adapter.py`（统一接口 → AutoCAD MCP 工具调用，接口预留）；`registry.py`（后端注册表 + `resolve_adapter` 能力检测 / 可用性探测 / 自动降级）。Agent 与 Pipeline 禁止直接调用 CAD API。
- `cad/capability/`（§12.2 Backend Capability System）：`backends.json` 声明各后端能力（line/polyline/block/dimension/layer/save_dwg/read_dwg…）；`capability.py` 提供能力检测（`has_capability`）、后端切换（`select_backend`）、降级处理（`missing_capabilities`）。
- `cad/mcp/autocad_mcp_client.py`（§12.3 AutoCAD MCP 接口预留）：`AutoCADMCPClient` 提供 connect / send_command / execute / query / disconnect，复用 Phase 7 `MCPClient` 传输层；本阶段不要求真实连接，未连接时由 Adapter 层降级到 Mock。
- `runtime/pipeline/cad_export.py`（§12.4/§12.5）：`translate_drawing_model`（DrawingModel → 后端中性实体，携带 tag/role 供回读对齐）、`export_drawing_to_dwg`（经统一 Adapter 导出 DWG，Pipeline 不知道具体 CAD 软件）、`read_dwg_to_generated_model`（DWG 回读 → GeneratedModel）、`round_trip_validate`（对比 LayoutModel：房间/墙/门窗数量、坐标误差、尺寸误差）、`run_dwg_round_trip`（一站式闭环）。
- `tests/cad/`（§12.6）：`test_adapter.py`（接口一致性/注册表/能力系统/降级，14 用例）、`test_mock_backend.py`（Mock 后端行为 + DrawingModel 生成 CAD 实体 + DWG 导出，12 用例）、`test_dwg_roundtrip.py`（Round-Trip 闭环 + 失配检测 + autocad 降级闭环，5 用例）。合计 31 个新用例。

### Changed
- `models/generated.py`（§12.5 完善 GeneratedModel）：新增 `dwg_path / layers / entities / dimensions / counts` 字段（均有默认值，向后兼容）。
- `runtime/pipeline/e2e_pipeline.py`（§12.4）：DRAWING 阶段新增 `_run_dwg_round_trip`——DrawingModel → CAD Adapter → DWG → 回读 → GeneratedModel → RoundTripReport（保存至 `models/GeneratedModel.json` 与 `validation/reports/RoundTripReport.json`）；state / checkpoint / finalize 增加 `dwg / generated_model / round_trip` 字段。
- `runtime/pipeline/stage_builders.py`：Mock 门/窗构造补充 `start/end` 线段派生字段（仅 Mock 构造器，不改变 LayoutModel SSOT 结构定义）。
- `cad/mcp/__init__.py`：导出 `AutoCADMCPClient`。
- `scripts/run_project.py`（验收日志）：新增最终日志 `CAD Backend: Mock/AutoCAD`、`DWG Generated`、`Round Trip Validation`、`Project Delivered`。

### Verified
- 全量测试 **206 passed**（Phase 11 为 178）；lint 0 错误。
- `python3 scripts/run_project.py examples/e2e/demo001.json` 实测：CAD Backend: Mock；DWG Generated（demo001.dwg）；Round Trip Validation: PASSED（room 9/9、wall 36/36、door 9/9、window 9/9、coord_err 0.005mm、dim_err 0.04mm）；Project Delivered。
- 交付说明：`examples/e2e/PHASE12_DELIVERY.md`；运行日志：`examples/e2e/phase12_e2e_run.log`。

## [2026-07-27] Phase 11：Runtime Integration & End-to-End Execution（COMPLETE）

> 将 InteriorDesignOS 从「架构完整、模块可测试」推进到「完整运行闭环」：一个命令启动一个完整设计项目，自动完成 Input → Orchestrator → Agent Graph → Runtime Pipeline → Artifacts → Validation → Export。遵守 PROJECT_RULES v1.1 / ARCHITECTURE v1.2 / WORKFLOW / Schema Contract v1.0；不新增 Agent、不修改 Schema Contract、不修改 LayoutModel SSOT、不接入真实 AutoCAD、不实现真实设计算法。

### Added
- `runtime/workspace/`（§4 Workspace 生命周期）：`WorkspaceManager` 建立标准目录结构（project.json / tasks / models/{original_model,design_spec,layout_model,professional_models,geometry_model,drawing_model,generated_model,validation_reports} / cad/{input,output} / validation/reports / logs），并在每次 Agent 产出后记录 §4 要求的六元元数据（输入版本 / 输出版本 / Agent / Task ID / Timestamp / Status）到 `tasks/task_history.json`。
- `runtime/checkpoint/`（§1/§2 断点）：`CheckpointManager` 保存/加载工程运行态（requirement / TaskGraph / produced 指针 / messages / conflict / approval / extra），供恢复。
- `runtime/resume/`（§1/§2 恢复）：`ResumeManager` 封装「从中断处续跑」入口（实际恢复由 `E2EPipeline._resume` 完成：读取 Checkpoint → 重建 TaskGraph 与内存产物 → 继续调度）。
- `runtime/registry/`（§3 注册表检查入口）：转发 `runtime.agent_registry` 并提供 `validate_all()`；`AgentCapabilityRegistry` 新增 `validate_contracts()` / `get_input_schema()` / `get_output_schema()` / `register()`，支持自动发现、注册、契约校验、输入/输出 Schema 查询（禁止硬编码）。
- `runtime/pipeline/stage_builders.py`（§5 上游/下游确定性构造器）：`build_original_model` / `build_design_spec` / `build_layout_model` / `build_deliverable`，明确标注为运行时集成 Mock（非真实 DWG 解析 / 非真实 AI 设计算法 / 非 Schema SSOT 修改），供闭环验证。
- `runtime/pipeline/e2e_pipeline.py`（§1/§2/§5/§7 完整运行时集成）：`E2EPipeline` 由 `OrchestratorAgent.build_full_graph` 生成完整 TaskGraph（parser→design→layout→专业(并行)→geometry→drawing→validator→deliverable），按依赖解析调度、专业 Agent 经契约 impl 动态加载、每轮保存 Checkpoint、失败重试、Conflict 网关 + Human Approval、Deliverable 装配、EventBus 事件发布；支持 `resume` 与测试用 `fail_after` 中断模拟。
- `agents/orchestrator/orchestrator_agent.py`：新增 `build_full_graph(requirement)` 自动发现专业 Agent（能力注册表 + 需求 disciplines + 具备 impl）串起全流程，Orchestrator 真正接管（分析目标 / 建图 / 依赖排序 / 调度 / 失败恢复 / 检查点恢复），不直接生成业务模型。
- `runtime/orchestrator/task_planner.py`：`ProjectRequirement` 扩展 E2E 结构化需求字段（rooms / area / story / style / features / materials / source），供 Mock 上游构造器使用（非 Schema Contract）。
- `runtime/pipeline/pipeline_runner.py`：新增 `run_e2e(requirement, resume=, ...)`，统一入口。
- `examples/e2e/demo001.json` + `examples/e2e/e2e_run.log`：100㎡ 三居室完整需求与运行日志。
- `scripts/run_project.py`（§6）：`python scripts/run_project.py examples/e2e/demo001.json` 一键启动完整项目，按阶段打印 `Project Started / Running: <agent> / Completed: <Output> / Project Delivered`。
- `tests/runtime/test_full_execution.py`（§7）：验证 Project 创建 / TaskGraph 生成 / Agent 调度 / Pipeline 执行 / Checkpoint 保存 / Resume 恢复 / 最终 Deliverable 生成 + 注册表自动发现与契约校验 + Workspace 六元元数据。

### Verified
- 一条命令启动完整项目（§5/§6）：`scripts/run_project.py examples/e2e/demo001.json` → 自动完成 parser→design→layout→6 专业 Agent(并行)→geometry→drawing(CAD Mock, 62 条命令)→validator(33 条协调冲突, 自动审批)→deliverable，产出 `workspace/projects/demo001/` 全量产物。
- 完整 Architecture 闭环（§验收）：Input → Orchestrator → Agent Graph → Runtime Pipeline → Artifacts → Validation → Export 全部贯通。
- Checkpoint + Resume（§7/§2）：测试在 `parser_task` 后模拟中断（抛出），Checkpoint 记录 parser COMPLETED、后续 PENDING；`run_e2e(resume=True)` 从中断处续跑至 DELIVERED，历史记录包含全部阶段。
- Workspace 六元元数据（§4）：`tasks/task_history.json` 每条记录含 task_id / agent / input_version / output_version / timestamp / status。
- 契约校验（§3）：`validate_all()` 对所有 `agents/*/agent_contract.json` 校验通过（无硬编码 Agent 列表）。
- 全量测试 **178 passed**（原 174 + 新增 4），无回归，无 lint 错误。
- 架构约束保持：**未**接入真实 AutoCAD MCP、**未**修改 LayoutModel SSOT / Schema Contract、**未**新增专业 Agent、**未**实现真实装修 / AI 设计算法、**未**增加 UI / 商业功能。

## [2026-07-27] Phase 10：Orchestrator Intelligence Layer v1.0（COMPLETE）

> 将固定 Pipeline 升级为动态 Agent Orchestration：Agent 自动发现 → TaskGraph 动态生成 → Schema 驱动路由 → 能力匹配 → 冲突处理 → Human Approval。输入一个项目需求，系统自动建项/分析/规划/找 Agent/执行/保存 Checkpoint/失败恢复，不再人工指定「先调用谁、后调用谁」。禁止：修改 CAD Framework / 修改 Schema 基础设计 / 真实装修算法 / AutoCAD / DWG 解析 / AI 设计算法 / 施工规范知识库。

### Added
- `runtime/agent_registry/`（§1 Agent Capability Registry）：将原 `runtime/agent_registry.py` 升级为包（向后兼容，历史符号从包顶层重新导出）。
  - `runtime_registry.py`：保留原「运行期 Agent 实例注册表」。
  - `registry.py`：新增 `AgentCapabilityRegistry`，自动扫描 `agents/*/agent_contract.json`，归一化 `agent_name/capabilities/input_schema/output_schema/dependencies/forbidden_actions`（兼容历史 `name`/`forbidden` 字段），提供 `find_agent_by_input()/find_agent_by_output()/find_agent_by_capability()/list_agents()`。**禁止硬编码 Agent**（全部来自目录扫描）。
- `agents/*/agent_contract.json`（§1 契约补全）：新增 electrical/lighting/plumbing/ceiling/construction/elevation 六份专业契约（含 discipline + impl）；为 geometry/drawing/validator 契约补充 `impl`/`dependencies`（增量、不改 Schema 基础设计）。
- `runtime/orchestrator/task_planner.py`（§2 Dynamic Task Planner）：`ProjectRequirement → TaskGraph`，数据流驱动的定点算法（输入 schema → 匹配 Agent → 生成任务 → 产出成为新输入），并按目标 schema 反向裁剪。自动生成 `layout_task → professional_tasks(并行) → geometry_task → drawing_task → validator_task`。
- `agents/orchestrator/orchestrator_agent.py`（§3 Orchestrator Agent）：`OrchestratorAgent`，负责分析目标 / 创建任务图 / 调度 / 处理失败 / 触发恢复，**不直接生成任何业务模型**（仅产出编排计划）。
- `runtime/router/schema_router.py`（§4 Schema Router）：`SchemaRouter`，依据 input/output schema 匹配 Producer→Consumer 形成自动数据流（`find_producer/find_consumer/route/build_flow`；专业模型经 `ProfessionalModels` 聚合流向 validator）。
- `runtime/conflict/resolver.py`（§5 Conflict Resolver）：`ConflictResolver` 检测专业协调冲突（电路/水管/吊顶/照明同一空间共存），输出 `ConflictReport`，存在阻断性冲突时 `requires_approval=True`（规则式协调标记，非真实碰撞检测）。
- `runtime/approval/approval.py`（§6 Human Approval）：`ApprovalRequest`（创建即 `WAITING_USER`）/`ApprovalResult`/`ApprovalManager`，支持 `approve`/`reject`。
- `runtime/pipeline/orchestrated_pipeline.py`（§7 Pipeline 改造）：`OrchestratedPipeline`，由 Orchestrator 生成 TaskGraph → 逐轮按依赖调度（专业 Agent 并行、其余串行）→ Agent 类由契约 `impl` 动态解析（不硬编码顺序）→ 专业深化后执行冲突网关 + Human Approval → 继续 Geometry/Drawing/Validation → 每轮保存 Checkpoint、支持失败重试恢复。
- `runtime/pipeline/pipeline_runner.py`：新增 `run_orchestrated(requirement, layout_model=...)` 统一入口。
- `examples/pipeline/run_orchestrated_demo.py`（§9）：输入项目需求，自动完成全流程，落盘 `orchestration_plan.json/task_graph.json/各模型/ConflictReport.json/approvals.json/ValidationReport.json`。
- `tests/orchestrator/`（§8）：`test_agent_discovery.py` / `test_task_planning.py` / `test_schema_router.py` / `test_conflict_resolver.py` / `test_human_approval.py` / `test_orchestrated_pipeline.py`，共 28 项。

### Verified
- Agent 自动发现（§8）：从 `agent_contract.json` 扫描出全部 Agent，指向空目录时发现 0 个（证明非硬编码）。
- Task 自动生成（§8/§9）：仅凭需求自动生成 `layout → 专业(并行) → geometry → drawing → validator`，依赖遵循数据流、拓扑有序、专业任务互不依赖（可并行）。
- Schema 匹配（§8）：Producer→Consumer 正确成边；专业模型经聚合流向 validator。
- 冲突处理 + Human Approval（§8）：同一空间跨专业共存被标记为冲突并 `requires_approval=True`，进入 `WAITING_USER`，approve/reject 状态机正确。
- 端到端（§9）：`python3 examples/pipeline/run_orchestrated_demo.py` → 自动建项/规划/执行，检出 19 条协调冲突并自动审批，mock 后端 42 条 CAD 命令，产出全部产物与 Checkpoint。
- 全量测试 **174 passed**（原 145 + 新增 28 + 其他），无回归，无 lint 错误；`runtime/agent_registry` 包化后既有导入全部兼容。
- 架构约束保持：**未**修改 CAD Framework / Schema 基础设计；未接入 AutoCAD / 未做 DWG 解析 / 未实现 AI 设计算法与施工规范知识库。

## [2026-07-27] Phase 9：Professional Deepening Pipeline v1.0（COMPLETE）

> 在 Phase 8 完整 Pipeline 基础上接入专业深化阶段：LayoutModel → Professional Agents → ProfessionalModels → Geometry/Drawing。支持 electrical / lighting / plumbing / ceiling / construction / elevation。禁止：真实装修 AI 设计 / 自动优化方案 / AutoCAD 直接操作。

### Added
- `models/professional/`（§1 专业模型契约）：
  - `base.py`：`ProfessionalModel(Model)` 统一基类（继承 metadata：project_id/agent/task_id/schema_version/timestamp 与 version：model_version/parent_version）+ `ValidationReport(Model)`。
  - `electrical.py` / `plumbing.py` / `lighting.py` / `ceiling.py` / `construction.py` / `elevation.py`：六类专业深化模型 dataclass（含 discipline + 业务内容字段），经 `ModelConverter` 序列化。
- `agents/`（§2 完善专业 Agent，输入 LayoutModel → 输出对应 ProfessionalModel）：
  - `electrical/electrical_agent.py`、`lighting/lighting_agent.py`、`plumbing/plumbing_agent.py`、`ceiling/ceiling_agent.py`、`construction/construction_agent.py`、`elevation/elevation_agent.py`：均为 `BaseAgent`，规则式派生专业内容（按房间面积/类型推导插座/灯具/给水管/吊顶平面等），**禁止直接输出 DWG**。
- `runtime/pipeline/professional_pipeline.py`（§3 专业 Pipeline）：
  - `ProfessionalPipeline`：`ThreadPoolExecutor` 并行调度全部专业 Agent（§3 明确并行组 Electrical/Lighting/Plumbing/Ceiling，Construction/Elevation 同等并行）；Agent 派生并行、版本打标串行（保证 ModelPipeline 线程安全）；随后复用 Geometry/Drawing Agent 与 `ProfessionalValidator`。
- `runtime/pipeline/pipeline_runner.py`（§4 接入 TaskGraph）：
  - 新增 `run(professional=True)` 与 `run_professional()`，在 `layout → geometry → drawing` 之间插入 **PROFESSIONAL_DEEPENING** 阶段（TaskGraph 含 `LAYOUT → PROFESSIONAL_DEEPENING → GEOMETRY → DRAWING → VALIDATION`），满足「Pipeline 包含 Stage5」。
- `agents/validator/validator_agent.py`（§5 专业 Validator）：
  - `ProfessionalValidator`：输入 LayoutModel + ProfessionalModels，检查 **空间冲突**（构件引用未知房间→ERROR/FAIL）、**尺寸冲突**（坐标落在房间边界外→WARN）、**专业规则**（湿区须有给排水器具 / 每房间须有插座与灯具 / 回路负载≤3000W），输出 `ValidationReport`（status/issues/rule_results/summary）。
- `examples/pipeline/`（§7）：`professional_demo.json`（100㎡ 三居室 LayoutModel）+ `run_professional_demo.py`，执行落盘 `workspace/projects/project/`（LayoutModel/ElectricalModel/LightingModel/PlumbingModel/GeometryModel/DrawingModel/ValidationReport 等）。
- `tests/integration/test_professional_pipeline_e2e.py`（§6）：Layout → Electrical/Lighting/Plumbing（并行）→ Geometry → Drawing + 专业模型 + ValidationReport 端到端验证；另含并行执行、模型结构、Validator 校验与冲突检测测试。（`test_professional_pipeline.py` 已存在于 `tests/professional/`，为避免 pytest 同名模块冲突，本阶段测试命名加 `_e2e` 后缀。）

### Verified
- 专业 Agent 可并行运行（§3/验收）；输出 6 个 ProfessionalModels（§1/§2 验收）。
- Validator 可检查专业结果（§5 验收）：独立测试注入未知房间引用 → 报告 status=FAIL 且含 SPATIAL_CONFLICT；正常 demo → PASS。
- Pipeline 包含 PROFESSIONAL_DEEPENING 阶段（§4/验收 Stage5）。
- 全量测试 **145 passed**（原 140 + 新增 6），无回归，无 lint 错误。
- `python3 examples/pipeline/run_professional_demo.py` → mock 后端执行 42 条 CAD 命令，产出全部 §7 要求文件，版本链连续。
- 架构约束保持：**未**破坏 CAD 抽象层（专业 Agent / Validator 仅产出模型与报告，不调用 AutoCAD）；未接入真实 AutoCAD、未开发 MCP Server、未做 AI 自动布局 / 装修算法优化。

## [2026-07-24] Phase 8：End-to-End Design Pipeline Integration v1.0（COMPLETE）

> 建立 InteriorDesignOS 第一条完整可运行流水线：Input → Project → Agent Pipeline → LayoutModel → GeometryModel → DrawingModel → CAD Command → Mock CAD Output。不追求真实装修智能设计，仅串联既有模块。禁止：接入真实 AutoCAD / MCP Server 开发 / AI 自动布局 / 装修算法优化。

### Added
- `models/`（§2 / §7 强类型模型层）：
  - `base/model.py`：`Model` 基类统一携带 `metadata`（project_id / agent / task_id / schema_version / timestamp）+ `version`（model_version / parent_version / producer_agent / timestamp）+ 版本链标签（layout/geometry/drawing_model_version）；`make_metadata` / `make_version` 工具。
  - `original.py` / `design.py` / `layout.py` / `geometry.py` / `drawing.py` / `generated.py`：六类模型 dataclass，经 `ModelConverter` 序列化。
  - `model_pipeline.py`：`ModelPipeline` —— 负责版本传递（OriginalModel→DesignSpec→LayoutModel→GeometryModel→DrawingModel→GeneratedModel），登记每步 model_type / version / parent_version / producer_agent / timestamp，提供 `verify_chain()` 连续性校验（§2 只做版本传递，不含业务转换）。
- `runtime/pipeline/`（§1 Pipeline Orchestrator，将旧 `pipeline.py` 转为 `pipeline/core.py` 以保留 9 处既有 import）：
  - `__init__.py`：向后兼容导出 `Pipeline` / `StageController` 等，并新增 `PipelineRunner`。
  - `pipeline_runner.py`：`PipelineRunner.run(layout_model)` 编排 —— 创建 Project、初始化 Context、创建 TaskGraph、调度 GeometryAgent + DrawingAgent、保存 checkpoint。**不含业务逻辑**。
- `agents/geometry/geometry_agent.py`（§3 Layout→Geometry 适配器）：输入 LayoutModel，输出 GeometryModel；坐标转换 / 房间边界转换 / 墙线生成 / 家具定位转换。**禁止生成 DWG（不调用任何 CAD 后端）**。
- `agents/drawing/agent.py`（§4 Geometry→Drawing 适配器）：新增 `build_drawing_model(geometry_model)` 静态方法，输入 GeometryModel 输出 DrawingModel（layers / entities / dimensions / annotations / titleblock）。**禁止直接调用 AutoCAD**（沿用既有 `DrawingModel → CommandQueue → CADSession → CADAdapter` 链路与 mock 执行）。
- `examples/pipeline/`（§5）：`demo_project.json`（100㎡ 三居室 LayoutModel）+ `run_demo.py`，执行落盘 `workspace/projects/demo/`（project.json / LayoutModel.json / GeometryModel.json / DrawingModel.json / drawing_command_log.json 等）。
- `tests/integration/test_full_pipeline.py`（§6）：Project 创建 → Agent 执行 → 模型生成 → CAD Mock 执行 → 文件输出 的端到端验证，全程无需人工干预（§8 验收）。

### Verified
- 全量测试 140 passed（原 136 + Phase 8 新增 4），无回归，无 lint 错误。
- 示例端到端：`python3 examples/pipeline/run_demo.py` → mock 后端执行 42 条 CAD 命令，产出 DrawingModel + drawing_command_log.json 于 `workspace/projects/demo/`。
- §8 验收满足：输入一个 LayoutModel，`PipelineRunner.run()` 得到 DrawingModel 与 drawing_command_log.json，全程无需人工干预。
- 架构约束保持：AutoCAD 是插件、CAD Framework 不感知、Agent 不调用 AutoCAD；本阶段未接入真实 AutoCAD、未开发 MCP Server、未做 AI 自动布局 / 装修算法优化。

## [2026-07-24] Phase 7：AutoCAD MCP Integration v1.0（COMPLETE）

> 在 Phase 6 CAD Framework 之上接入真实 AutoCAD 后端。不修改 CAD Framework 架构、绕过 CADAdapter、让 Agent 直接调用 AutoCAD 或写死 AutoCAD API。仅完成真实 CAD 执行通道。

### Added
- `cad/mcp/`（§1 MCP Client Layer，不感知 CAD 业务、不依赖 Agent/Runtime）：
  - `mcp_exception.py`：`MCPError` / `MCPConnectionError` / `MCPToolError`。
  - `mcp_protocol.py`：JSON-RPC 信封 + AutoCAD MCP 工具名（`cad.*`），集中翻译避免写死 AutoCAD 原生 API。
  - `mcp_client.py`：`MCPClient`（connect/disconnect/call_tool/send_command/query_state）+ 可注入 `MCPTransport`（抽象）+ `HTTPMCPTransport`（JSON-RPC over HTTP，仅标准库）。
- `cad/autocad/autocad_adapter.py`（§2 真实实现）：`AutoCADAdapter(CADAdapter)` 实现全部 14 方法，所有绘制经注入的 `MCPClient` 转译为 `cad.*` 工具；`export()` 仅向 MCP 请求导出，**绝不直接生成 DWG**；支持注入 `client`（测试用 FakeMCPClient）。
- `cad/__init__.py`：`build_cad_backend(name, config, output_dir)` 增强 —— `name` 缺省从 `config["cad"]["backend"]` 取；`autocad` 时从 `config["autocad"]` 注入 `host/port/timeout`（禁止代码写死）；`output_dir` 仅转发 mock。
- `config/runtime.yaml`：新增 `cad.backend` 与 `autocad.host/port/timeout`（§4）。
- `runtime/config.py`：`_parse_simple` 支持嵌套键（`cad.backend`），退路亦能解析（§4 不写死）。
- `agents/drawing/agent.py`（§5）：接受 `cad_config` 并按配置解析 `backend`，透传 `build_cad_backend`；保持 `DrawingModel → CommandQueue → CADSession → CADAdapter` 链路，永不 `import autocad_adapter`。
- `main.py`：`cad` 子命令从配置解析 `backend` 并注入 `cad_config`。
- `tests/cad/test_autocad_adapter.py`（§6）：连接/断开、命令执行（Line/Polyline/Text/Dimension）、错误处理（MCP 断开 / 命令失败 / 事务回滚）、导出经 MCP 不直接生成 DWG。
- `tests/architecture/test_cad_dependency.py`（§7）：`agents/*` 与 `runtime/*` 不得 `import cad.autocad`；`CADSession` 仅依赖抽象 `CADAdapter`；`cad/mcp` 不依赖上层。
- `docs/CAD_FRAMEWORK.md` 升 v1.1：新增 Phase 7 Extension（MCP Client Layer / 后端切换 / 完整执行通道 / 架构护栏），§7 由占位改为真实实现，更新 §9/§10/§11 完成标准。

### Verified
- 全量测试 136 passed（原 124 + Phase 7 新增 12），无回归，无 lint 错误。
- CLI 端到端：`python3 main.py cad DEMO` → mock 后端执行并写出 `drawing_command_log.json`；`--backend autocad`（未配置 host）优雅失败提示「未配置 MCP transport」。
- §7 架构护栏三项全部满足：AutoCAD 是插件 ✅、CAD Framework 不感知 AutoCAD ✅、Agent 不调用 AutoCAD ✅；功能三项：Mock 可运行 ✅、可切换 AutoCAD backend ✅、DrawingCommand 经 MCP 可执行 ✅。

## [2026-07-24] Phase 6：CAD Integration Foundation（COMPLETE）

> 仅建立 CAD 抽象框架，不连接真实 AutoCAD、不生成 DWG、不写死 MCP / CAD 软件 API。Phase 6 COMPLETE → 可进入 Phase 7 AutoCAD MCP Integration。

### Added
- `cad/` 抽象层（禁止 import runtime/orchestrator/agents/professional）：
  - `cad/base/cad_adapter.py`：`CADAdapter` 抽象接口（connect/disconnect/open_document/save/close/create_layer/draw_line/draw_polyline/draw_arc/draw_circle/insert_block/create_text/create_dimension/export，共 14 方法）+ 上下文管理器 + `CAD_ADAPTER_METHODS`。
  - `cad/base/cad_document.py`：`CADDocument`（打开文档抽象，承载图层/图元）。
  - `cad/base/cad_transaction.py`：`CADTransaction` + `TransactionState`（PENDING→ACTIVE→COMMITTED|ROLLED_BACK 状态机）+ `CADTransactionError`（单事务模型，禁止嵌套 begin）。
  - `cad/base/cad_session.py`：`CADSession`（连接/文档/事务/命令队列 生命周期；`begin/commit/rollback`、`run(queue, transactional=True)` 批量执行且失败自动 rollback）。
  - `cad/command/drawing_command.py`：`DrawingCommand` 基类 + 通用图元命令（CreateLayer/DrawLine/DrawPolyline/DrawArc/DrawCircle/InsertBlock/CreateText）+ `DrawingCommandQueue` + `COMMAND_REGISTRY`（命令回放）。
  - `cad/command/{wall,door,window,furniture,dimension}_command.py`：5 个领域命令（委托通用图元，表达领域语义）。
  - `cad/mock/`：`MockAdapter`（内存后端，记录执行历史，`export()` 输出 `drawing_command_log.json`）+ `MockDocument`。
  - `cad/autocad/autocad_adapter.py`：`AutoCADAdapter`（Phase 6 仅占位，全部方法 `raise NotImplementedError`，指向 Phase 7）。
  - `cad/validator.py`：`CADValidator`（非法 command / 非法 layer / 非法 transaction / 非法 entity 四类校验）。
- `cad/__init__.py`：`CAD_BACKENDS` 插件注册表 + `build_cad_backend(name, **kwargs)` 按名加载后端（插件机制）。
- `agents/drawing/agent.py`：`DrawingAgent`（Phase 6 §6）：`DrawingModel(+可选 GeometryModel)` → `DrawingCommandQueue` → `CADSession` + 注入的 `CADAdapter`（默认 mock）。**不直接操作任何 CAD 实现**；输出经 `ArtifactManager` 落盘 `cad/drawing_command_log.json`，路径回填 `context.outputs`。
- `tests/cad/`（6 文件）：`test_cad_adapter` / `test_cad_session` / `test_transaction` / `test_command` / `test_mock_backend` / `test_drawing_pipeline`，覆盖 Adapter / Session / Transaction / Command / MockBackend / DrawingPipeline。
- `tests/architecture/test_import_dependency.py`：依赖矩阵新增 `cad`（禁止反向依赖 runtime/orchestrator/agents/professional）。
- `docs/CAD_FRAMEWORK.md` v1.0：Adapter 架构 / Command Pattern / Session 生命周期 / Backend 插件机制 / 完成标准。
- `main.py`：新增 `cad <project_id> [--model <drawing_model.json>] [--backend mock]` 子命令，驱动 CAD Framework 端到端验证。

### Verified
- 全量测试 124 passed（原 110 + Phase 6 新增 14），无回归，无 lint 错误。
- CLI 端到端：`python3 main.py cad DEMO` → 14 条命令经 mock 后端执行并写出 `drawing_command_log.json`。
- §10 完成标准 6 项全部满足：DrawingAgent 不直接操作 CAD ✅、CAD 后端插件化 ✅、Mock CAD 可运行 ✅、Command Queue 可执行 ✅、AutoCAD Adapter 已预留 ✅、测试通过 ✅。

## [2026-07-24] Phase 5.1：Professional Framework Stabilization（COMPLETE）

> 架构固化，无新增功能。Phase 5.1 COMPLETE → 可进入 Phase 6 CAD Integration Foundation。

### Added
- `core/`：架构基础层（最底层，禁止反向依赖）——`core/context/agent_context.py`（`AgentContext`：project_id / task_id / agent_name / workspace / inputs / outputs / metadata；`Result` / `BaseAgent` / `make_metadata` / `STAGES` 从 orchestrator 下沉至 core）、`core/artifact/artifact_manager.py`（`ArtifactManager`：save / load / exists / archive / delete + 版本归档 `archive/<name>.<UTC>.json`、原子写入）、`core/logging.py`（`NullLogger` / `JsonFileLogger` / `build_logger`，替代 professional 对 `runtime.logger` 的依赖）。
- `models/base/model_converter.py`：`ModelConverter`（dataclass ↔ dict/json 双向转换，递归嵌套；禁止 Agent 自行处理 JSON）。
- `professional/base/rule_engine.py`：`BaseRuleEngine`（Agent 管流程 / RuleEngine 管专业规则 / Model 只承载数据）。
- 8 个专业 RuleEngine：`<discipline>_rules.py`（electrical / plumbing / lighting / ceiling / flooring / hvac / construction / furniture），原 Agent `_build_model()` 专业规则全部迁入；Agent 收敛为 `discipline + rule_engine_class` 两行声明。
- `tests/architecture/`（Phase 5.1 §11）：`test_import_dependency.py`（AST 扫描：professional/core/models 禁止 import runtime / orchestrator / agents）、`test_artifact.py`（professional 无直接文件写入 + 输出必经 `ArtifactManager.save` + 生命周期/版本归档）、`test_context.py`（AgentContext 字段契约 + 所有 Agent `run(context)` 单参签名 + context 内联输入 + `context.workspace` 生效）。

### Changed
- `professional/base/professional_agent.py`：解除对 runtime / orchestrator 的全部依赖（只依赖 core / models / schemas）；统一流程 `validate_input → generate_model → publish_result`；新增 `publish_result(model, context)`（输出经 ArtifactManager，路径回填 `context.outputs`）；`export_model` 保留为兼容接口（内部同样经 ArtifactManager）；删除 workspace 硬编码（`context.workspace → 注入 workspace_root → core.PROJECTS_DIR`）；输入支持 `inputs.layout` / `inputs.layout_path` 内联传递。
- `professional/base/professional_model.py`：补齐 `to_json()` / `from_dict()` / `from_json()`（经 ModelConverter，Phase 5.1 §7 强类型化闭环）。
- `professional/validator.py`：`REPO_ROOT` 改从 `core` 获取（原依赖 `runtime`）。
- `agents/orchestrator/agent.py`：`STAGES` / `make_metadata` / `Result` / `AgentContext` / `BaseAgent` 改为从 `core.context` re-export（向后兼容，orchestrator → core 单向依赖）。
- `professional/__init__.py`：`build_professional_agents` 新增 `logger` 注入参数（Runtime 可注入 UnifiedLogger，鸭子类型兼容）。
- `docs/PROFESSIONAL_FRAMEWORK.md` v1.1：新增 §1.1 Dependency Rules（Runtime→Orchestrator→Agent→RuleEngine→Model，禁止反向依赖）、更新目录结构 / 生命周期（publish_result + RuleEngine 分层）/ §8 架构测试说明。

### Verified
- 全量测试 97 passed（原有 87 + 架构测试新增 10，无回归），无 lint 错误。
- Phase 5.1 §13 完成标准全部满足：Professional 不依赖 Runtime / 不依赖 Orchestrator ✅、Agent 经 Context 获取数据 ✅、Agent 不直接读写文件 ✅、ArtifactManager 统一管理输出 ✅、ProfessionalModel 强类型化（to_json/from_json）✅、RuleEngine 与 Agent 分离 ✅、架构测试通过 ✅。

## [2026-07-23] Phase 5：Professional Deepening Framework（v1.0）

### Added
- **Phase 5：全部专业设计 Agent 的统一框架**（8 个 Professional Agent，Mock Logic；禁止 AutoCAD MCP / 生成 DWG / 调用外部 AI）。
- `professional/`：`base/professional_agent.py`（`BaseProfessionalAgent` 统一提供 load_layout / load_design_spec / validate_input / generate_model / export_model / quality_check，LayoutModel 与 DesignSpec 只读深拷贝、禁止修改）、`base/professional_model.py`（`BaseProfessionalModel` 公共 dataclass + objects 汇总序列化）、`validator.py`（`ProfessionalValidator` 聚合校验）。
- 8 个专业目录（§2/§5/§6）：electrical（switches/sockets/lights/circuits/panel）、plumbing（water_supply/drain/equipment）、lighting（fixtures/groups/controls）、ceiling（ceiling_regions/levels/materials）、flooring（areas/materials/patterns）、hvac（air_supply/return_air/equipment）、construction（notes/details/specifications）、furniture（movable/fixed/clearance），各含 `<d>_agent.py` + `<d>_model.py`，全部继承基类、仅实现 `_build_model()`（Mock 示例数据）。
- `schemas/professional/professional_model.schema.json`：公共 ProfessionalModel Schema（§4：metadata / layout_model_version / discipline / objects / constraints / quality；八专业枚举；`additionalProperties:false` 禁止 CAD/DWG/Entity/Layer 字段）；`schemas/examples/ProfessionalModel.example.json` 同步更新。
- `runtime/parallel.py`：`ParallelStageRunner`（§8 Parallel Stage：Fan-out/Fan-in、部分失败隔离、只重跑失败作业、作业异常转失败 Result）。
- Orchestrator（§7）：`run_professional_stage()` 并行启动全部 Professional 任务（经 Dispatcher 调度，Fan-out → Fan-in，失败任务复位 READY 单独重跑）。
- Pipeline（§10 Mock Workflow）：`run_professional()`（LayoutModel → Parallel Agents → Validator 聚合 → Export 清单 + `professional_validation_report.json` + `checkpoint_professional_v1.json`；缺省回退示例 LayoutModel）；`main.py` 新增 `professional` 子命令；`examples/professional/mock_workflow.py` 演示（Electrical/Lighting/HVAC/Furniture）。
- 测试（§11）：`tests/professional/` 35 项（professional_agent / professional_model / parallel_execution / professional_validator / version_check / schema_check / professional_pipeline e2e）。
- 文档（§12）：新增 `docs/PROFESSIONAL_FRAMEWORK.md`（生命周期 / ProfessionalModel / 并行机制 / Validator 聚合 / 版本一致性）；`docs/architecture.md` 升级 v1.2（新增 §16 Professional Deepening Framework）。

### Changed
- `runtime/agent_registry.py`：新增 `PROFESSIONAL_AGENTS`（8 专业），`build_default` 注册全部 Professional Agent。
- `agents/orchestrator/dispatcher.py`：`execute()` 新增 `save_checkpoint` 参数（并行阶段由 Fan-in 后统一保存检查点，避免并发写同一 stage 文件）。
- `runtime/pipeline.py`：新增 `PROFESSIONAL_STAGE`；`_on_task_done` 忽略非主链路阶段（并行阶段统一收尾）。

### Verified
- 全量测试 87 passed（原有 52 + Phase 5 新增 35，无回归），无 lint 错误。
- CLI 实测：`python main.py professional <id>` 8 专业并行全部 COMPLETED、聚合校验 passed、Export 清单与检查点落盘；`python examples/professional/mock_workflow.py` 四专业演示流程完整跑通。
- §14 完成标准全部满足：框架建立 / 8 Agent 可运行（Mock）/ Schema 完成 / Orchestrator 并行深化 / Runtime Parallel Stage（部分失败只重跑失败者）/ Validator 多专业聚合校验 / 测试全过。
- 禁止项守约：未实现 DWG / AutoCAD MCP / 外部 AI；LayoutModel 与 DesignSpec 只读未修改。

## [2026-07-23] Phase 4：Design Agent（v1.0）

### Added
- **Phase 4：第一个具备 AI 决策能力的 Design Agent** —— 把「用户需求 + OriginalModel」固化为统一的 `DesignSpec`（系统所有设计决策的唯一来源 SSOT），不负责 CAD/布局/绘图。
- `schemas/design/design_spec.schema.json`：DesignSpec Schema（§1，必填 13 字段；`additionalProperties:false` 禁止 CAD/Geometry/Drawing/Layer/Entity/DWG）。
- `agents/design/`：`design.py`（主入口：解析→组装→Schema 校验→落盘 `design_spec.json` v1 + `checkpoint_design_v1.json`→统一 `Result`）、`requirement_parser.py`（§3 UserRequirement）、`constraint_parser.py`（§4 ConstraintSet）、`style_planner.py`（§5 多标签风格）、`budget_planner.py`（§6 LOW/MEDIUM/HIGH/PREMIUM + 分配）、`family_analyzer.py`（§7 FamilyProfile）、`material_planner.py`（§8 材料偏好，禁止品牌）、`validator.py`（按 design_spec.schema.json 校验）、`result_builder.py`（统一 Result）、`exceptions.py`（复用统一 error_handler）、`README.md` + 占位文档补全为真实 Design Agent 文档。
- 注册表接入：`runtime/agent_registry.py` 的 `design` 由占位升级为真实 `DesignAgent`（Dispatcher 经注册表获取，禁止写死）。
- Pipeline：`runtime/pipeline.py` 新增 `DESIGN_SPEC` 阶段（§13：INITIALIZATION→INPUT_ANALYSIS→ORIGINAL_MODEL→DESIGN_SPEC，Design 完成即终止，Layout 暂不进入）；新增 `run_design()` 直接运行 Design Agent；任务重试前将 `FAILED` 复位为 `READY`（§13.1）。
- `status.py` / `PROJECT` 阶段枚举增补 `DESIGN_SPEC`；`main.py` 新增 `design` 子命令（§14）+ `run` 的 `--requirement` 选项。
- 示例：`examples/design/`（small_apartment / three_room / villa / office 输入包 + `DesignSpec.example.json`）；`schemas/examples/DesignSpec.example.json` 同步更新为新 schema。
- 测试：`tests/design/`（test_requirement_parser / test_constraint_parser / test_style_planner / test_design_spec / test_design_pipeline）+ `tests/e2e/test_project_pipeline.py` 覆盖到 DESIGN_SPEC 完成标准。

### Changed
- `runtime/agent_registry.py`：`build_default` 注册真实 `DesignAgent`，`PLACEHOLDER_AGENTS` 移除 `design`。
- `runtime/pipeline.py`：`SUPPORTED_STAGES` 增补 `DESIGN_SPEC` 并设为 `TERMINAL_STAGE`；`_process_stage` 增加 `DESIGN_SPEC` 分支；Workspace 文件列表含 `design_spec.json`。
- `runtime/status.py`：`SUPPORTED_STAGES` 增补 `DESIGN_SPEC`。
- 重写 `schemas/design/design_spec.schema.json` 与 `schemas/examples/DesignSpec.example.json` 为 Phase 4 §1 字段（原示例为旧形态，非约束文档，可改）。

### Verified
- 全量测试 52 passed（Phase 3 原有 23 + Phase 3.5 新增 12 + Phase 4 新增 17，无回归）。
- CLI 端到端：`create→run(--requirement)→status`（终态 COMPLETED / DESIGN_SPEC / 进度 1.0，original_model + design 任务均 COMPLETED）；`design` 子命令直跑 Design Agent 成功。
- 生成的 `design_spec.json` 经 `design_spec.schema.json` 校验通过，字段正确（style/budget/family/constraints/materials 等），无禁止字段。
- 完成标准 §18 全部满足：Schema 完成 / Agent 可独立运行 / 可解析需求与 OriginalModel / 可生成 DesignSpec / Schema 校验通过 / Workspace+Checkpoint 自动保存 / Dispatcher 可调度 / Pipeline 可运行至 DesignSpec / 全部测试通过。
- 禁止项（§17 Design 不负责 Layout/Geometry/CAD/DWG/Drawing/AutoCAD MCP/家具摆放/墙体生成/尺寸计算）均未实现；下游 Layout/Geometry 等仍占位。
- 4 份约束文档（PROJECT_RULES / ARCHITECTURE / WORKFLOW / SCHEMA_DESIGN）未修改。

## [2026-07-23] Phase 3.5：End-to-End Project Pipeline（v1.0）

### Added
- **Phase 3.5：第一条真正可运行的端到端 Project Pipeline**（create → run → resume → status，遵守 4 份约束文档，未实现任何下游业务 Agent）
- `runtime/pipeline.py`：Pipeline Runner（§1 仅流程控制）+ `StageController`（§3 阶段顺序：INITIALIZATION→INPUT_ANALYSIS→ORIGINAL_MODEL）+ Project 生命周期状态机（§2：CREATED→INITIALIZING→RUNNING→WAITING→COMPLETED→FAILED→CANCELLED，不跳跃、全记录日志）
- `runtime/agent_registry.py`：统一 Agent 注册表（§5：parser 真实实现 + design/layout/geometry/drawing/validator/repair/export 占位，Dispatcher 经注册表获取，禁止写死）
- `runtime/config.py` + `config/runtime.yaml`：§12 统一配置（workspace_path / log_level / checkpoint_interval / schema_validation / auto_save / max_retry），禁止硬编码
- `runtime/status.py`：§11 状态查询（Current Project / Stage / Task / Progress / Running Agent / Elapsed Time）
- `main.py`：§10 统一 CLI（create / run / resume / status），仅调用 Runtime
- 集成测试：`tests/runtime/`（test_pipeline / test_resume / test_checkpoint / test_registry / test_workspace / test_event_bus）+ `tests/e2e/test_project_pipeline.py`
- §9 统一事件流：EventBus 新增 ProjectCreated / ProjectStarted / StageStarted / StageCompleted / TaskCompleted / CheckpointSaved / WorkspaceUpdated / ProjectCompleted / ProjectFailed
- §7 Workspace 自动更新（project.json / task_graph.json / original_model.json，覆盖旧版本并记录更新时间）；§8 Checkpoint 自动恢复（resume_project 恢复 Project / TaskGraph / Stage / Context）

### Changed
- `agents/orchestrator/dispatcher.py`：`execute` 成功后发布 `TASK_COMPLETED` 并经 `stage_advancer` 回调推进阶段（§4，不写死 Agent）；类型提示补 `Callable`
- `agents/orchestrator/orchestrator.py`：新增组件访问属性（dispatcher / checkpoint / task_graph 可写 / event_bus / logger / project_runtime 等），供 Pipeline 调度复用（§1）
- `runtime/project_runtime.py`：`STATES` 增补 Phase 3.5 Project 生命周期状态（CREATED / INITIALIZING / WAITING）
- `agents/orchestrator/task_graph.py`：`TaskGraph` 新增只读 `tasks` 属性

### Verified
- 全量测试 35 passed（Phase 3 原有 23 + Phase 3.5 新增 12，无回归）
- CLI 端到端：`create→run→status→resume` 全过；Project 完成状态 COMPLETED / ORIGINAL_MODEL / 进度 1.0
- 完成标准 §15 全部满足：Project 可创建/运行、Dispatcher 调度 Parser、Parser 返回 Result、Stage 自动切换、Workspace 自动更新、Checkpoint 自动保存、Checkpoint 可恢复、EventBus 正常工作、CLI 可运行、E2E Pipeline 全过
- 未实现 Design/Layout/Geometry/Drawing/Validator/Repair/Export Agent 及 AutoCAD/LLM/CAD（§14 禁止项均未实现）

## [2026-07-23] Phase 3：Parser Agent v1.0

### Added
- **Phase 3：第一个真正工作的业务 Agent —— Parser**（系统入口，把输入解析为统一数据模型 OriginalModel）
- `agents/parser/`：`parser.py`（主流程串联：加载→识别→归一化→建模→校验→落盘→检查点→Result）、`input_detector.py`（输入类型识别 → `InputType`：DWG/DXF/PDF/IMAGE/TEXT/ZIP/UNKNOWN，扩展名+魔数兜底）、`input_loader.py`（加载/存在性/大小/sha256 Hash/MIME，不解析业务）、`normalizer.py`（统一路径/编码/单位/坐标/文件名 → `InputContext`）、`model_builder.py`（构建 OriginalModel，6 必填字段，几何可空数组，禁止 null）、`validator.py`（用 `cad/original_model.schema.json` 校验，失败抛 `ValidationError`）、`result_builder.py`（统一 `Result`，`next_tasks=["design"]`）、`exceptions.py`（复用 orchestrator 统一异常）、`README.md`
- 输入识别覆盖：DWG / DXF / PDF / PNG / JPG / JPEG / JSON / TXT / ZIP / 未知类型
- Workspace 落盘：`workspace/projects/<id>/original_model.json`（v1）
- Checkpoint：`workspace/projects/<id>/checkpoint_parser_v1.json`（stage / OriginalModel / task_status / project_status）
- 统一日志（ISO8601）：Parser Started / Input Loaded / Input Type / Schema Validation / Workspace Saved / Checkpoint Saved / Parser Finished
- 示例数据：`examples/input/`（empty_project / sample_json / sample_image / sample_pdf / sample_dwg_placeholder），DWG 使用占位文件（无 AutoCAD）
- 单元测试：`tests/parser/`（test_input_loader / test_detector / test_original_model / test_schema_validation / test_parser_pipeline），覆盖正常/空/错误/Schema 不合法/不存在文件 + Dispatcher + Orchestrator 集成
- 演示脚本：`scripts/demo_parser.py`

### Verified
- 单元测试全过：Parser 独立运行成功、自动识别输入类型、生成合法 OriginalModel、Schema 校验通过、Workspace/Checkpoint 落盘、Dispatcher 调用、Orchestrator 调度、统一 Result 返回
- 演示脚本验证 Phase 3 §16 全部完成标准
- 收尾：补全 `agents/parser/` 占位文档（role/prompt/input/output/workflow/schema/example/memory/todo/checklist）为真实 Parser 文档；修复 `demo_parser.py` 中 `demo_dispatcher` 未传 `input_refs` 导致 Dispatcher 集成 `FAILED` 的问题（现端到端 3 段全过）
- 未修改 PROJECT_RULES / ARCHITECTURE / WORKFLOW / SCHEMA_DESIGN 及任何租房算法/CAD/LLM（§15 禁止项均未实现）

## [2026-07-23] Phase 2：Orchestrator Framework v1.0

### Added
- **Phase 2：Orchestrator 控制核心框架**（仅框架，不含装修算法 / CAD / LLM）
- `runtime/`：`logger.py`（统一日志，ISO8601，runtime/agent/error 三文件）、`message.py`（事件类型与 Event 对象）、`event_bus.py`（发布/订阅）、`project_runtime.py`（Project 生命周期与落盘）、`session.py`（会话装配）
- `agents/orchestrator/`：`orchestrator.py`（顶层驱动）、`dispatcher.py`（单任务分发，经注册表调用 Agent）、`scheduler.py`（默认 DAG 构建 + 就绪任务）、`state_manager.py`（12 阶段严格顺序状态机）、`context_manager.py`（上下文读取/保存，只读语义）、`task_graph.py`（DAG + 任务状态机 + 环检测）、`error_handler.py`（Recoverable/Fatal/Validation 三类异常归一）、`checkpoint.py`（每阶段版本化快照 + 恢复）、`agent.py`（统一 `Result` / `AgentContext` / `BaseAgent` / `StubAgent` / `AgentRegistry`）、`__init__.py`
- `workspace/` 首次运行自动创建 `projects/`、`cache/`、`logs/`、`artifacts/`
- 事件发布/订阅：`TaskCreated` / `TaskStarted` / `TaskFinished` / `TaskFailed` / `StageChanged` / `ProjectFinished`
- 统一异常分类，禁止 `print()`、禁止直接退出程序
- 测试与演示：`tests/test_orchestrator_smoke.py`、`scripts/demo_orchestrator.py`

### Verified
- 冒烟测试全过：完整运行 COMPLETED、事件发布齐全、恢复跳过已完成、失败不崩溃归入 FAILED
- 演示脚本验证 Phase 2 §15 全部完成标准（创建 Project / TaskGraph / 调度虚拟 Agent / 切换 Stage / 保存 Checkpoint / 恢复 / 日志 / 事件 / 管理 Context / 框架完整运行）

## [2026-07-22] Schema Contract v1.1 (Hardening)

### Changed
- **Phase 1.5：Schema Contract Hardening**（依据 `SCHEMA_REFACTOR_PLAN`）：将契约从「设计级文档」升级为「可执行数据契约」
- `core/metadata.schema.json`：由空文件补齐为统一元数据契约，含 `quality`（$ref validation/quality.schema.json），作为所有模型 `$ref` 的 SSOT
- `validation/validation_report.schema.json`：由空文件补齐为校验报告契约（validation_id/project_id/passed/checks/errors/quality），驱动 Repair Loop
- 全部模型 metadata 改为相对 `$ref: ../core/metadata.schema.json`，消除重复定义；`scripts/validate_schema.py` 改为 Registry 感知，自动解析跨文件 `$ref`
- 核心模型 `additionalProperties:false`（layout/geometry/drawing/generated/validation_report），双保险强化 SSOT
- `layout_model.schema.json`：新增 `walls`/`doors`/`windows` 空间事实字段（墙体/门/窗归 LayoutModel 负责，不属 CAD）

### Added
- `schemas/design/design_spec.schema.json`：Stage 3 设计方案说明契约（style/requirements/rooms_function/materials/standards）
- `schemas/professional/professional_model.schema.json`：Stage 5 专业深化基础契约（metadata/layout_model_version/professional_type/elements/validation）
- `geometry_model.schema.json`：新增 `geometry_model_version`，支持 Geometry→Drawing 版本追踪
- `drawing_model.schema.json`：完善 `dimension` 契约（dimension_id/geometry_ref/value/unit/start/end）
- `room/space.schema.json`：rooms 改为 `$ref ./room.schema.json`，消除房间定义分裂
- 新增示例：ValidationReport.example.json / DesignSpec.example.json / ProfessionalModel.example.json
- 新增示例（补充校验覆盖）：Metadata.example.json / OriginalModel.example.json / GeneratedModel.example.json
- `docs/SCHEMA_DESIGN.md` 升版至 v1.1，同步关系图与目录清单

### Verified
- 6 个示例（LayoutModel/GeometryModel/DrawingModel/ValidationReport/DesignSpec/ProfessionalModel）全部 PASS；负向用例（注入 cad_layer、缺必填）正确报错

## [2026-07-22] Schema Contract v1.0

### Added
- **Phase 1：Schema Contract Design** 完成，建立全链路 JSON 数据契约（Draft 2020-12）
- `schemas/core/`：metadata.schema.json（统一元数据）、task.schema.json（任务状态机）
- `schemas/project/project.schema.json`：工程状态，含 12 阶段枚举
- `schemas/room/`：room.schema.json、space.schema.json
- `schemas/cad/`：original_model / layout_model(SSOT) / geometry_model / drawing_model / generated_model 五模型 Schema
- `schemas/validation/`：validation_report.schema.json（文件/模型/规范三级）、quality.schema.json
- `schemas/examples/`：LayoutModel（100㎡三居室）、GeometryModel、DrawingModel 示例，均通过校验
- `agents/<9>/agent_contract.json`：orchestrator/parser/design/layout/geometry/drawing/validator/repair/export 输入输出契约
- `scripts/validate_schema.py`：Draft 2020-12 校验器（PASS / ERROR 输出，支持单文件与目录批量）
- `docs/SCHEMA_DESIGN.md` v1.0：Schema 关系图、数据流、Agent 契约表、SSOT 与版本策略
- LayoutModel 显式禁止 cad_layer/dwg_entity/drawing_command；DrawingModel 禁止 design_decision；共享 metadata/room 内联以保证 validator 可离线运行

## [2026-07-22] WORKFLOW v1.0

### Added
- `docs/WORKFLOW.md` **v1.0**：定义完整装修施工图生成流程，含 Mermaid 总览图与 Stage 0–11 标准阶段（目标/输入/输出/Agent/Skills/Schemas/Standards/Validation/Failure Handling/Human Approval）
- 遵守 `PROJECT_RULES.md` v1.1 与 `ARCHITECTURE.md` v1.1；不创建 Agent/Skill/Schema，仅定义业务流程
- 流程约束摘要表衔接 SSOT、DWG 往返、Model First、人工审核、任务状态机、断点恢复、模板只读、动态工作流等规则

## [2026-07-22] ARCHITECTURE Patch v1.1

### Added
- `docs/architecture.md` 升级至 **v1.1**，新增 §13 CAD Round-trip Architecture、§14 CAD 数据闭环原则（Model First）、§15 Agent 输入版本声明
- §8 Single Source of Truth 新增 **LayoutModel Version Chain**（版本链 + 版本元数据 + 不可覆盖规则）
- §4 核心数据流增强：`LayoutModel → GeometryModel → DrawingModel → DWG → GeneratedModel → Validation → Export` 三中间层
- Geometry Agent 定位调整为几何中间层（空间几何/墙体/门窗/家具/尺寸链/标注基准/CAD 基础数据），输出 `GeometryModel.json`
- 引入 **DrawingModel** 中间层，避免 Drawing Agent 直接操作 LayoutModel
- 新增 Schema：`schemas/cad/drawing_model.json`（sheets/layers/entities/annotations/dimensions/blocks/titleblock）
