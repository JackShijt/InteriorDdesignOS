# PROJECT_RULES

> **最高约束文件（Supreme Constraint）**
>
> 本文件定义 `InteriorDesignOS` 工程的**最高规则**。
> 所有 Agent、Skill、Standard、Schema、Script 与文档**必须**遵守本文件，不得与之冲突。
> 当任何模块的内部约定与本文件不一致时，**以本文件为准**。
> 后续新增模块必须在文件头显式声明：
> `本模块遵守 PROJECT_RULES.md 的最高约束。`

---

## 1. 项目目标

1.1 构建一个由多智能体（Multi-Agent）协作驱动的室内设计自动化操作系统，将"需求 → 全套专业施工图纸与交付物"的链路标准化、可复用、可验证。

1.2 系统必须保证输出的每一份图纸、每一个数据对象都**可追溯、可校验、符合现行国家与行业规范**。

1.3 在不牺牲规范合规性的前提下，最大化并行度与自动化程度，减少人工干预与跨专业冲突。

1.4 系统是可演进的：通过 `standards/`、`knowledge/`、`schemas/`、`skills/` 的分层沉淀，使专业能力随项目积累而增长。

---

## 2. 架构原则

2.1 **分层解耦**：系统自上而下分为 `调度层(Orchestrator) → 代理层(Agents) → 能力层(Skills) → 约束层(Standards/Schemas/Knowledge) → 工具层(MCP) → 存储层(Workspace)`。上层可调用下层，下层不得反向依赖上层。

2.2 **一切皆可配置**：规范、模板、图层、样式、命名规则一律以文件形式存放在 `standards/`、`templates/`、`schemas/` 中，禁止将硬规则写死在代码逻辑里。

2.3 **声明式优先**：Agent 之间的协作通过结构化消息（JSON）与 Schema 约束表达，而非隐式共享内存。

2.4 **最小可信依赖**：每个 Agent 只依赖其所需的标准、Schema 与 MCP 工具；新增依赖必须登记在对应 `agent/*.md` 的文档中。

2.5 **可中断可恢复**：任何长流程必须支持断点续跑，状态外置于 `workspace/` 与日志，不得仅存于内存。

---

## 3. 单一职责原则（SRP）

3.1 每个 Agent **只承担一个专业领域**的职责，不得越界处理其它 Agent 的核心任务。例如 `electrical` 不绘制给排水管线，`plumbing` 不布置灯具。

3.2 每个 Skill **只封装一项可复用能力**（如"按国标校验插座间距"），不得混合多个无关能力。

3.3 当一项任务涉及多专业，必须由 Orchestrator 拆分后分发给对应 Agent 并行处理，结果由 Orchestrator 汇总；**禁止**某个 Agent 私自串行包揽全流程。

3.4 跨专业冲突统一由 `validator` / `constraint` / `cad_validator` 裁决，业务 Agent 自身不做最终合规判定。

---

## 4. 数据流原则

4.1 所有 Agent 间传递的数据必须是**符合 `schemas/` 定义的 JSON 对象**，禁止传递非结构化自由文本作为正式数据载体。

4.2 数据流向为单向有向：上游 Agent 产出 → Orchestrator 路由 → 下游 Agent 消费。下游不得将脏数据回写上游，冲突须经 Orchestrator 协调。

4.3 每个数据对象必须携带最小元数据：`project_id`、`agent`、`task_id`、`timestamp`、`schema_version`。

4.4 **不可变中间产物**：已通过验证的 Agent 输出写入 `workspace/output/` 后视为不可变；修订须生成新版本，不得原地覆盖丢失历史。

4.5 几何坐标统一采用 **毫米(mm)**，面积采用 **平方米(m²)**，角度采用 **度(°)**，原点与朝向以 `schemas/core/` 定义为基准。

---

## 5. 文件命名规范

5.1 目录与文件统一使用**小写英文 + 下划线**分隔（kebab-case 仅用于文档标题展示，物理文件名用 snake_case）。

5.2 Agent 目录名 = 代理 ID（如 `cad_validator`、`layout`）；每个 Agent 目录内固定包含 10 个标准文件：`role/prompt/workflow/input/output/memory/schema/example/checklist/todo.md`。

5.3 图纸文件命名格式：
`<项目编号>_<图别>_<图号>_<图名>.dwg`
示例：`Project_001_P-01_平面布置图.dwg`
图别前缀约定：`P`=平面，`E`=电气，`W`=给排水，`L`=照明，`C`=吊顶，`V`=立面，`F`=地面，`D`=详图。

5.4 版本管理：修订稿追加 `_v2`、`_v3` 后缀，不覆盖原文件。

5.5 禁止在文件名中使用空格、中文标点、特殊字符（`\ / : * ? " < > |`）。

---

## 6. JSON Schema 使用规范

6.1 所有跨 Agent 数据结构必须在 `schemas/` 下拥有对应的 **JSON Schema (draft 2020-12)** 文件，文件名与结构名一致（如 `schemas/room/room.json`）。

6.2 每个 Agent 的 `schema.md` 必须声明其输入/输出所引用的 Schema 文件 URI，禁止凭空约定字段。

6.3 数据在 Agent 入口**必须先校验后处理**；校验失败立即进入失败重试或上报流程（见第 9 节），不得带着未知结构继续执行。

6.4 Schema 变更必须递增 `schema_version` 并在 `CHANGELOG.md` 记录，**向后不兼容变更**须保留旧版本一段时间。

6.5 字段命名统一 `snake_case`；枚举值使用大写英文（如 `"status": "COMPLETED"`）。

---

## 7. AutoCAD MCP 调用原则

7.1 所有对 AutoCAD 的自动化写操作必须通过受支持的自动化接口完成，例如 AutoCAD MCP、AutoCAD API 或未来经 Tool Registry 注册的 CAD 自动化工具，禁止直接操作文件或假设 CAD 内部状态。项目不得将具体工具实现写死于架构规则中，以保证未来具备可扩展性（Tool Registry 见第 15 节）。

7.2 调用前必须确认当前图纸模板来自 `templates/cad/`（含图层、文字样式、标注样式、图框），不得自行发明图层名。

7.3 图层命名严格遵循 `standards/cad/layer_naming` 与 `templates/cad/layer/`；新增图层须先在该标准登记。

7.4 每次 MCP 调用必须是**幂等可重放**的：相同参数重复调用应得到一致结果，以支持断点恢复（见第 10 节）。

7.5 MCP 调用须带超时与错误处理；超时或异常按第 9 节重试，连续失败须上报 Orchestrator，不得静默丢弃绘图指令。

7.6 所有通过 MCP 生成的图元，其来源（`agent`、`task_id`）应写入图纸摘要或扩展数据(XData)，保证可追溯。

---

## 8. 禁止猜测用户意图

8.1 当用户输入存在**歧义、缺失关键信息或含多种合理解读**时，Agent **必须**向用户澄清，禁止自行假设并继续。

8.2 需要澄清的典型场景：户型面积/房间数缺失、风格未指定且影响专业结论、规范选择冲突（如地方标准 vs 国标）、特殊需求不明。

8.3 澄清应以结构化问题形式提出（选项 + 默认建议），并说明"若不选择将采用何种保守默认"，但**保守默认不等于猜测**——仅用于不阻断流程的可选兜底，且须在输出中显式标注。

8.4 任何"未确认假设"都必须在输出与日志中打标（`assumption: true`），便于用户复核。

---

## 9. 失败重试机制

9.1 所有外部调用（MCP、文件 IO、网络）必须包裹超时与异常捕获，**不允许未处理异常导致整个流程崩溃**。

9.2 可重试错误（超时、临时不可用、并发冲突）采用**指数退避**重试，最多 3 次，间隔 `1s → 2s → 4s`。

9.3 不可重试错误（Schema 校验失败、规范冲突、权限不足）**立即中止**当前任务并上报 Orchestrator，由 Orchestrator 决策（澄清用户 / 调用 repair / 终止）。

9.4 每次重试必须记录：重试次数、错误类型、触发参数、结果；进入 `logs/` 与任务状态。

9.5 重试耗尽后仍失败，任务标记为 `FAILED` 并保留现场（输入、中间产物、日志），供人工或断点恢复介入。

---

## 10. 日志与可追溯性要求

10.1 系统级日志写入 `logs/`，按 `YYYY-MM-DD.log` 滚动；任务级日志写入 `workspace/projects/<id>/run.log`。

10.2 每条关键操作日志至少包含：`timestamp`、`project_id`、`agent`、`task_id`、`action`、`input_ref`、`output_ref`、`status`。

10.3 所有产出文件（图纸、JSON、报告）必须可追溯到：由哪个 Agent、基于哪版 Schema、引用哪些标准、由哪次任务生成。

10.4 禁止记录用户隐私敏感信息；日志中仅保留项目必需的技术元数据。

10.5 Orchestrator 维护全局任务时间线，任何 Agent 可通过 `task_id` 查询前序依赖的产出，确保链路可审计。

---

## 11. 断点恢复机制

11.1 每个任务在启动时于 `workspace/projects/<id>/state.json` 写入初始状态；每完成一个阶段，按第 13 节 Task State Machine 原子更新阶段状态（如 `PENDING → READY → RUNNING → VALIDATING → COMPLETED`）。

11.2 流程中断（崩溃、手动停止、超时）后重启，Orchestrator 读取 `state.json`：**已完成阶段跳过，从首个未完成阶段续跑**，已产出的不可变中间产物直接复用。

11.3 续跑时若上游产物因外部原因丢失，Orchestrator 触发该上游阶段重算，不影响下游已验证部分（除非依赖确实变更）。

11.4 所有 MCP 绘图指令需满足第 7.4 节幂等要求，使续跑不会重复生成图元或产生重复图层。

11.5 恢复完成后，在 `run.log` 标记 `RESUMED_AT <timestamp>` 及续跑起点，保证过程透明。

---

## 12. 输出验证要求

12.1 任何 Agent 在返回结果前，必须按自身 `checklist.md` 完成自检，并产出验证声明（`status` + 校验清单结果）。

12.2 图纸类产出在交付前**必须经过** `cad_validator`（图层/标注/图幅规范）与 `validator`（专业合规）双重校验，任一项不通过则进入 `repair` 或退回上游。

12.3 校验须基于 `schemas/` 与 `standards/` 的机器可读规则，优先自动化，人工抽检仅作补充。

12.4 最终交付物（DWG/PDF）生成后，Export Agent 须执行"文件可打开、图层完整、图框正确、命名合规"四项终检，全部通过方可标记 `DELIVERED`。

12.5 验证结果随交付物一并归档至 `workspace/output/`，作为质量凭证长期保留。

---

## 13. 任务状态机（Task State Machine）

13.1 所有任务必须采用统一生命周期状态。允许状态集合：

`PENDING` / `READY` / `RUNNING` / `WAITING_USER` / `WAITING_AGENT` / `RETRYING` / `VALIDATING` / `REPAIRING` / `COMPLETED` / `FAILED` / `CANCELLED`

13.2 状态语义：
- `PENDING`：等待调度
- `READY`：满足执行条件
- `RUNNING`：正在执行
- `WAITING_USER`：等待用户输入
- `WAITING_AGENT`：等待其它 Agent 完成
- `RETRYING`：正在自动重试
- `VALIDATING`：正在执行校验
- `REPAIRING`：正在自动修复
- `COMPLETED`：任务完成
- `FAILED`：执行失败
- `CANCELLED`：任务取消

13.3 所有 Agent 必须显式维护自己的任务状态，状态变更须写入 `workspace/projects/<id>/state.json` 并进入日志。

13.4 Orchestrator 必须根据任务状态决定是否进入下一阶段：仅当上游为 `COMPLETED` 且下游 `READY` 时方可调度；遇 `WAITING_USER`/`WAITING_AGENT` 须挂起等待，`FAILED`/`CANCELLED` 须终止或上报。

---

## 14. 能力声明（Capability Discovery）

14.1 所有 Agent 在启动时必须声明自身元信息，供 Orchestrator 动态调度：

```json
{
  "agent": "layout",
  "version": "1.0",
  "capabilities": ["layout.build", "layout.optimize"],
  "dependencies": ["DesignSpec.schema.json"],
  "supported_schemas": ["LayoutModel.schema.json"],
  "outputs": ["LayoutModel.json"]
}
```

14.2 声明至少包含：`Agent Name`、`Version`、`Capabilities`、`Dependencies`、`Supported Schemas`、`Outputs`。

14.3 Orchestrator 应基于 Agent 的 Capability 自动决定任务分配，**禁止将调用关系写死**；新增/下线 Agent 仅需更新其声明即可被系统感知。

---

## 15. 工具注册表（Tool Registry）

15.1 所有外部工具必须统一注册于 Tool Registry，方可被 Agent 调用。注册范围包括但不限于：AutoCAD MCP、Blender、3ds Max、SketchUp、Photoshop、Computer Use、Revit。

15.2 每个工具至少声明：`Name`、`Version`、`Supported Commands`、`Availability`。

15.3 Agent **禁止直接假设工具存在**；调用前必须通过 Tool Registry 查询工具可用性，不可用时按第 9 节上报，不得静默 fallback 到未注册实现。

---

## 16. 动态工作流（Dynamic Workflow）

16.1 Workflow 不应固定。Orchestrator 必须综合以下因素动态生成 Task Graph：用户需求、当前任务、已完成阶段、Agent 能力、Tool 可用性。

16.2 工作流应最小化执行路径。例如用户仅要求生成水电图时，无需执行完整施工图流程，仅调度 `plumbing`/`electrical` 及相关校验、导出即可。

16.3 动态生成的 Task Graph 必须可被日志记录（第 10 节）与断点恢复（第 11 节）复现。

---

## 17. 人工审核节点（Human Approval）

17.1 对于关键阶段 —— `Layout`、`Design`、`Construction`、`Final Drawing` —— 系统必须支持人工审核，审核通过后方可进入下一阶段。

17.2 审核动作支持：`Approve`、`Reject`、`Comment`。

17.3 若审核未通过（`Reject`），必须退回对应 Agent 修正后重新提交，**禁止在审核未过时继续执行下游**。

17.4 所有审核记录（操作人、动作、意见、时间戳）必须进入日志系统（第 10 节），作为可追溯凭证。

---

## 18. 质量评分（Quality Evaluation）

18.1 所有 Agent 输出必须附带质量评估，至少包含：

```json
{
  "confidence": 0.97,
  "quality_score": 93,
  "validation_passed": true
}
```

18.2 `validation_passed` 必须为 `true` 方可进入下游；`quality_score` 低于阈值或 `confidence` 不足时，Orchestrator 应视情况转入 `REPAIRING` 或 `WAITING_USER`。

18.3 Repair Agent 可根据质量评分决定是否自动修复；修复后须重新评估并满足第 12、18 节验证要求。

---

## 19. DWG 往返验证（DWG Round-trip Validation）

19.1 所有 DWG 在生成完成后必须重新验证，流程如下：

```
DWG → 重新打开 → 重新解析 → GeneratedModel.json
    → Compare → LayoutModel.json → Validation
```

19.2 若 DWG 无法重新打开，或 `GeneratedModel.json` 与 `LayoutModel.json` 不一致，则视为生成失败，进入第 9 节失败流程。

19.3 **禁止直接交付未经 Round-trip Validation 的 DWG**；验证通过方可标记 `DELIVERED`（见第 12.4 节）。

---

## 20. 模板只读原则（Template Protection）

20.1 `templates/` 中所有资源属于**只读资源**，任何 Agent 不得直接修改模板。

20.2 正确流程：`打开 Template → 复制到 Workspace → 修改副本 → 生成输出`。

20.3 模板仅用于生成，不允许覆盖；对模板的任何修正需求须通过变更流程更新 `templates/` 源文件并在 `CHANGELOG.md` 记录，而非在运行时就地改写。

---

## 21. 知识元数据（Knowledge Metadata）

21.1 `knowledge/` 下所有知识文件必须包含统一元数据，至少包括：`Source`、`Version`、`Date`、`Author`、`Confidence`。

21.2 所有知识必须具有明确来源；**禁止引用未知来源内容作为正式规范**，引用时应标注来源与置信度。

21.3 知识文件版本随 `Version` 字段递增，重大修订须记录于 `CHANGELOG.md`。

---

## 22. 单一可信源（Single Source of Truth）

22.1 当 `DesignSpec.json` 与 `LayoutModel.json` 完成验证后，`LayoutModel.json` 即成为整个工程的**唯一可信空间模型（Single Source of Truth）**。

22.2 后续所有 Agent（包括但不限于 `Geometry`、`Drawing`、`Construction`、`Electrical`、`Plumbing`、`Lighting`、`Export`）**禁止重新解释用户需求、禁止重新推导设计方案、禁止自行修改设计**，必须完全基于 `LayoutModel.json` 工作。

22.3 若在某下游环节发现设计问题，必须退回 `Design` 或 `Layout` 重新生成，**不得在下游 Agent 中自行修正设计**。

22.4 任何对空间模型的变更只能经由 `Design`/`Layout` 经 Human Approval（第 17 节）后产生新的 `LayoutModel.json` 版本，下游据此刷新。

---

## 引用声明

> 本工程所有模块（Agents / Skills / Standards / Schemas / Scripts）均遵守本 `PROJECT_RULES.md` 的最高约束。
> 本文件版本：`v1.1`　最后更新：`2026-07-22`（含 Patch 01–11 增补）
