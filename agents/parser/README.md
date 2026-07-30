# Parser Agent（Phase 3 · v1.0）

系统入口 Agent。负责把 **输入（DWG / PDF / 图片 / 用户信息）** 解析为统一数据模型
**OriginalModel**，经 Schema 校验、落盘 Workspace、写 Checkpoint，返回统一 `Result`。

> Parser 不负责设计，不负责 CAD 绘图（Phase 3 §14）。当前为**占位解析**：无真实 CAD
> 几何提取；无法解析时几何数组为空（禁止返回 null）。

## 模块结构

| 文件 | 职责 | 对应规则 |
| --- | --- | --- |
| `input_detector.py` | 识别输入类型 → `InputType`（DWG/DXF/PDF/IMAGE/TEXT/ZIP/UNKNOWN） | §2 |
| `input_loader.py` | 加载文件、检查存在性、大小、Hash(sha256)、MIME（不解析业务） | §3 |
| `normalizer.py` | 统一路径/编码/单位/坐标/文件名 → `InputContext` | §4 |
| `model_builder.py` | 构建 `OriginalModel`（6 必填字段，几何可空数组） | §5 |
| `validator.py` | 用 `original_model.schema.json` 校验，失败抛 `ValidationError` | §6 |
| `result_builder.py` | 构造统一 `Result`（success/output_model/messages/quality/next_tasks） | §10 |
| `parser.py` | 串联上述步骤，落盘 Workspace + Checkpoint，返回 `Result` | §7/§8/§11 |
| `exceptions.py` | 统一异常：`RecoverableError` / `ValidationError` / `FatalError` | §12 |

## 处理闭环

```
输入
  ↓ Input Loader     （存在性 / 大小 / Hash / MIME）
  ↓ Input Detector   （识别 InputType）
  ↓ Normalizer       （统一 InputContext）
  ↓ Model Builder    （OriginalModel）
  ↓ Schema Validation（original_model.schema.json，失败即中止）
  ↓ Workspace        （workspace/projects/<id>/original_model.json  v1）
  ↓ Checkpoint       （workspace/projects/<id>/checkpoint_parser_v1.json）
  ↓ Result           （统一 Result，next_tasks=["design"]）
```

## 输入类型识别

| 扩展名 | InputType |
| --- | --- |
| `.dwg` | DWG |
| `.dxf` | DXF |
| `.pdf` | PDF |
| `.png` / `.jpg` / `.jpeg` | IMAGE |
| `.json` / `.txt` | TEXT |
| `.zip` | ZIP |
| 其他 | UNKNOWN（按魔数兜底猜测，仍失败则为 UNKNOWN） |

## 用法

### 独立运行

```python
from agents.parser import run_parser

result = run_parser("examples/input/sample_json/sample.json", project_id="demo")
print(result.success, result.output_model["metadata"]["project_id"])
```

### 受 Orchestrator / Dispatcher 调度

```python
from agents.parser import ParserAgent
from agents.orchestrator import Orchestrator, AgentRegistry, StubAgent
from runtime.project_runtime import STAGES

reg = AgentRegistry()
for s in STAGES:
    reg.register(ParserAgent() if s == "ORIGINAL_MODEL" else StubAgent(agent_name=s.lower()))
orch = Orchestrator("demo", registry=reg)
orch.graph.get_task("original_model-demo").input_refs = ["examples/input/sample_json/sample.json"]
orch.run()
```

## 约束

- 遵守 `PROJECT_RULES.md` / `ARCHITECTURE.md` / `WORKFLOW.md` / `SCHEMA_DESIGN.md`（不得修改）。
- 禁止 `print()` / `sys.exit()`；异常统一为 `RecoverableError` / `ValidationError` / `FatalError`。
- 禁止 AutoCAD MCP、CAD 绘图、LLM 推理、Design/Layout/Geometry/Drawing/Repair Agent 及任何装修算法（§15）。
