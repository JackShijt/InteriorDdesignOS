# CAD_FRAMEWORK

> **CAD Integration Foundation 规范** · v1.1（Phase 6 + Phase 7）

- **Phase 6**：建立 CAD 抽象框架（Adapter / Session / Command / Mock / 校验）。
- **Phase 7**：在框架之上接入真实 AutoCAD 后端 —— MCP Client Layer + AutoCADAdapter（经 MCPClient 委托）+ 后端插件工厂 + Mock→AutoCAD 切换。**不修改 CAD Framework 架构、绕过 CADAdapter、让 Agent 直接调用 AutoCAD 或写死 AutoCAD API。**

---

## 1. 目录结构

```text
cad/
├── __init__.py                  # 统一导出 + CAD_BACKENDS 插件注册表 + build_cad_backend
├── base/
│   ├── cad_adapter.py           # CADAdapter（后端抽象接口，14 个方法）
│   ├── cad_document.py          # CADDocument（打开的图纸文档抽象）
│   ├── cad_transaction.py       # CADTransaction（事务状态机）
│   └── cad_session.py           # CADSession（连接/事务/命令队列 生命周期管理）
├── command/
│   ├── drawing_command.py       # DrawingCommand 基类 + 通用图元命令 + DrawingCommandQueue
│   ├── wall_command.py          # WallCommand（墙体）
│   ├── door_command.py          # DoorCommand（门）
│   ├── window_command.py        # WindowCommand（窗）
│   ├── furniture_command.py     # FurnitureCommand（家具）
│   └── dimension_command.py     # DimensionCommand（尺寸标注）
├── mcp/                         # Phase 7 §1：MCP Client Layer（封装通信，不感知 CAD 业务）
│   ├── mcp_exception.py         # MCPError / MCPConnectionError / MCPToolError
│   ├── mcp_protocol.py          # JSON-RPC 信封 + AutoCAD MCP 工具名（协议层，非 AutoCAD 原生 API）
│   └── mcp_client.py            # MCPClient（connect/disconnect/call_tool/send_command/query_state）+ 可注入 transport
├── mock/
│   ├── mock_adapter.py          # MockAdapter（内存后端，记录执行历史）
│   └── mock_document.py         # MockDocument（内存文档）
├── autocad/
│   └── autocad_adapter.py       # AutoCADAdapter（Phase 7 经 MCPClient 接入真实 AutoCAD）
└── validator.py                 # CADValidator（command / layer / transaction / entity 校验）

agents/
└── drawing/
    └── agent.py                 # DrawingAgent（DrawingModel → CommandQueue → CADAdapter）

tests/cad/                       # Phase 6 测试（6 文件，覆盖 Adapter/Session/Transaction/Command/Mock/Pipeline）
```

---

## 2. 分层与依赖规则

```text
Runtime
    |
Orchestrator
    |
Agent（agents/drawing）
    |
CAD Framework（cad/）
    |
core / models / schemas
```

- `cad/` 仅依赖 `core` / `models` / `schemas` 与标准库 / 三方库。
- `cad/` **禁止** import `runtime` / `orchestrator` / `agents` / `professional`
  （由 `tests/architecture/test_import_dependency.py` AST 静态强制）。
- `agents/drawing` 可依赖 `core` 与 `cad`，但**不直接调用任何 CAD 后端**。
- 禁止：直接调用 AutoCAD、直接生成 DWG、写死 MCP、写死 CAD 软件 API。

---

## 3. CADAdapter（§2 后端抽象接口）

所有后端必须实现以下方法（见 `cad/base/cad_adapter.py` 与 `CAD_ADAPTER_METHODS`）：

| 类别 | 方法 |
| --- | --- |
| 连接/文档 | `connect` `disconnect` `open_document` `save` `close` |
| 图层 | `create_layer` |
| 几何图元 | `draw_line` `draw_polyline` `draw_arc` `draw_circle` |
| 块/文字/标注 | `insert_block` `create_text` `create_dimension` |
| 导出 | `export` |

`CADAdapter` 同时提供上下文管理器（`__enter__`/`__exit__` → connect/disconnect），便于 try/finally 安全释放。

---

## 4. CAD Session（§3 生命周期）

`CADSession` 管理 **Document + Transaction + Command Queue**：

```text
session = CADSession(adapter)
session.open(project_id)          # connect + open_document
   ├─ begin()                    # 新建 ACTIVE 事务（单事务模型，禁止嵌套）
   ├─ execute(command)           # 在事务内执行单条命令（委托 CADAdapter）
   ├─ commit()                   # 事务 → COMMITTED，记录并入 committed_records
   └─ rollback()                 # 事务 → ROLLED_BACK，丢弃 provisional 记录
session.run(queue)               # begin → execute* → commit（任一条失败自动 rollback）
session.close()                  # 关闭文档 + disconnect
```

事务状态机（`CADTransaction` / `TransactionState`）：`PENDING → ACTIVE → COMMITTED | ROLLED_BACK`；
非 ACTIVE 状态下 `add_command/commit/rollback` 一律抛 `CADTransactionError`。

---

## 5. Drawing Command（§4 命令模式）

DrawingAgent **不直接调用 CAD**，而是构造 `DrawingCommand`，交由 `CADSession` 在注入的 `CADAdapter` 上执行。

- `DrawingCommand`（抽象基类）：`execute(adapter)` + `to_dict()` + `from_dict()`（经 `COMMAND_REGISTRY` 重建，支持回放）。
- 通用图元命令（与 `CADAdapter` 接口一一对应）：`CreateLayerCommand` `DrawLineCommand` `DrawPolylineCommand` `DrawArcCommand` `DrawCircleCommand` `InsertBlockCommand` `CreateTextCommand`。
- 领域命令：`WallCommand` `DoorCommand` `WindowCommand` `FurnitureCommand` `DimensionCommand`（内部委托通用图元，表达领域语义）。
- `DrawingCommandQueue`：有序命令集合，`to_dict()` / `from_dict()` 支持序列化。

数据流（§6）：

```text
DrawingModel (+ 可选 GeometryModel)
        ↓  DrawingAgent._build_queue（仅翻译，不画）
DrawingCommandQueue
        ↓  CADSession.run
CADAdapter（mock / autocad / 未来插件）
        ↓  export
drawing_command_log.json
```

---

## 6. Mock CAD Backend（§5）

`MockAdapter`（`cad/mock/mock_adapter.py`）：

- 实现 `CADAdapter` 全部接口；方法只把调用记录进 `execution_log` 并返回记录 dict（不连接真实软件）。
- `export(path=None)`：导出执行历史；若给定 `path` 或构造时 `output_dir`，则写入 **`drawing_command_log.json`**（含 `backend` / `command_count` / `log`）。
- 用于测试、回放与框架验证（`tests/cad/test_mock_backend.py`）。

---

## 7. AutoCAD Adapter（Phase 7 实现）

`AutoCADAdapter`（`cad/autocad/autocad_adapter.py`）：

- 与 `MockAdapter` 同构，注册为 `CAD_BACKENDS["autocad"]`。
- **实现 `CADAdapter` 全部 14 个方法**，所有绘制调用通过注入的 `MCPClient`
  转译为 AutoCAD MCP 服务暴露的 `cad.*` 工具（`cad.draw_line` 等）。
- **不直接生成 DWG、不调用 AutoCAD 原生 API**；`export()` 仅向 MCP 请求导出。
- 可注入 `client`（测试用 FakeMCPClient），生产环境按 `host/port/timeout`
  （来自 `config/runtime.yaml`）构造 `MCPClient`。

---

## Phase 7 Extension（AutoCAD MCP Integration）

### MCP Client Layer（§1）

`cad/mcp/` 封装与 AutoCAD MCP 服务的通信，**不知道 CAD 业务**、不依赖 Agent / Runtime：

- `MCPClient.connect/disconnect/call_tool/send_command/query_state`。
- `MCPTransport`（抽象）+ `HTTPMCPTransport`（JSON-RPC over HTTP，仅标准库）。
- `mcp_protocol.py`：集中定义工具名与消息信封，使 `AutoCADAdapter` 只做
  「CADAdapter 调用 → (工具名, 参数)」翻译，**不写死任何 CAD 软件 API**。

### 后端切换（§3 / §五）

依赖方向（唯一允许的访问链）：

```text
MockAdapter ─┐
             ├─► CADAdapter 接口
AutoCADAdapter ┘      │
                      │ 继承
                      ▼
              CADSession → CADAdapter → AutoCADAdapter → MCPClient → AutoCAD MCP → AutoCAD
```

`build_cad_backend(name, config, output_dir)` 按名加载后端；`name` 缺省时从
`config["cad"]["backend"]` 取（默认 `mock`）；`autocad` 时从
`config["autocad"]` 注入 `host/port/timeout`（**禁止代码内写死**）。

### 完整执行通道（Phase 7 验收）

```text
LayoutModel → GeometryModel → DrawingModel
   → DrawingAgent（仅翻译，不画）
   → DrawingCommandQueue
   → CADSession（事务：begin → execute* → commit / rollback）
   → AutoCADAdapter（CADAdapter 实现）
   → MCPClient（call_tool: cad.*）
   → AutoCAD MCP
   → AutoCAD
```

### 架构护栏（§七）

- `agents/*` 不得 `import cad.autocad` / `autocad_adapter`（Agent 不调用 AutoCAD）。
- `runtime/*` 不得 `import cad.autocad` / `autocad_adapter`。
- 允许：`cad/autocad` 继承 `cad/base/cad_adapter.CADAdapter`；`cad/__init__`
  经插件注册表加载 `autocad`（同包内引用）。
- 由 `tests/architecture/test_cad_dependency.py` 静态强制。

---

## 8. CAD Command Validation（§8）

`CADValidator`（`cad/validator.py`）四大检查维度：

1. **非法 command**：`command_type` 必须登记在 `COMMAND_REGISTRY`。
2. **非法 layer**：图层命名 `^[A-Z][A-Z0-9_]{0,30}$`（大写开头、仅含 A-Z0-9_、≤31 字符）。
3. **非法 transaction**：必须是 `CADTransaction` 实例，状态机完整性。
4. **非法 entity**：实体 `type` 来自白名单（`WALL/DOOR/WINDOW/FURNITURE/DIMENSION/AXIS/COLUMN/FIXTURE/EQUIPMENT`），且引用图层合规。

`DrawingAgent.run` 在构建队列前 `assert_valid(model=...)`、构建后 `assert_valid(commands=...)`，任一校验失败返回失败 `Result`。

---

## 9. 后端插件机制

```python
from cad import build_cad_backend, CAD_BACKENDS, CADSession

# Mock：按 output_dir 落盘 drawing_command_log.json
adapter = build_cad_backend("mock", output_dir=workspace)

# AutoCAD：参数经 config 注入（禁止代码写死）
adapter = build_cad_backend("autocad",
                            config={"autocad": {"host": "127.0.0.1",
                                                "port": 8000, "timeout": 30}})
```

`CAD_BACKENDS` 为 `{name: CADAdapter 子类}` 注册表。新增后端 = 实现 `CADAdapter` + 注册一行；`DrawingAgent` 通过 `backend=` / `config["cad"]["backend"]` 按名加载，**零代码改动**。

---

## 10. 测试（§9）

`tests/cad/`（8 文件）：

- `test_cad_adapter.py`：`CADAdapter` 接口实现、AutoCADAdapter 委托 MCPClient、`build_cad_backend` 工厂。
- `test_cad_session.py`：Session 生命周期、事务批量执行、`committed_records`、嵌套 begin 拒绝、自动 rollback。
- `test_transaction.py`：`CADTransaction` 状态机合法/非法转移。
- `test_command.py`：各命令 `execute` 产生正确 op、序列化/反序列化往返、注册表完整性。
- `test_mock_backend.py`：Mock 后端记录历史、`export` 写出 `drawing_command_log.json`、回放可用。
- `test_autocad_adapter.py`：**Phase 7** 连接/断开、命令执行（Line/Polyline/Text/Dimension）、错误处理（MCP 断开 / 命令失败 / 事务回滚）、导出经 MCP 不直接生成 DWG。
- `test_drawing_pipeline.py`：DrawingAgent 端到端（mock 成功 / 非法图层失败 / autocad 优雅失败 / 期望命令类型）。

架构约束：

- `tests/architecture/test_import_dependency.py`：将 `cad` 纳入禁止反向依赖扫描。
- `tests/architecture/test_cad_dependency.py`：**Phase 7** 强制 `agents/*`、`runtime/*` 不得 `import cad.autocad`；`CADSession` 仅依赖抽象 `CADAdapter`；`cad/mcp` 不依赖上层。

---

## 11. 完成标准（§10 / Phase 7）

### 架构

| 标准 | 满足 |
| --- | --- |
| AutoCAD 是插件 | ✅ `AutoCADAdapter` 注册于 `CAD_BACKENDS`，经 `build_cad_backend` 加载 |
| CAD Framework 不感知 AutoCAD | ✅ `cad/` 仅经插件注册表引用，`cad.base` 不 import `cad.autocad` |
| Agent 不调用 AutoCAD | ✅ `agents/drawing` 只 `from cad import ...`，`test_cad_dependency.py` 静态强制 |

### 功能

| 标准 | 满足 |
| --- | --- |
| 可 Mock 模式运行 | ✅ `MockAdapter` 落盘 `drawing_command_log.json`，CLI `main.py cad` 验证 |
| 可切换 AutoCAD backend | ✅ `config/runtime.yaml` 的 `cad.backend` / `--backend`，`host/port/timeout` 由配置注入 |
| DrawingCommand 可真实执行 | ✅ `AutoCADAdapter` 经 `MCPClient.call_tool(cad.*)` 转译执行（测试用 FakeMCPClient 验证） |

### 流程

```text
LayoutModel → DrawingAgent → DrawingCommandQueue → CADSession
           → AutoCADAdapter → MCPClient → AutoCAD MCP → AutoCAD
```

本阶段**仅完成真实 CAD 执行通道**；禁止自动设计 / AI 布局优化 / DWG 解析 / 施工图生成算法。

完成后进入后续阶段。
