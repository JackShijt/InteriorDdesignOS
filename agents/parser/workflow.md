# Parser Agent - Workflow

## 工作流定位
本代理处于 InteriorDesignOS 流水线**最前端（ORIGINAL_MODEL 阶段）**，由 Orchestrator 调度、经 Dispatcher 执行。

## 标准步骤（对应 parser.py::_process）
1. **Input Loader** —— 加载文件，检查存在性 / 大小 / Hash(sha256) / MIME（不解析业务）。
2. **Input Detector** —— 识别 `InputType`（扩展名 + 魔数兜底）。
3. **Normalizer** —— 统一路径 / 编码 / 单位 / 坐标 / 文件名，生成 `InputContext`。
4. **Model Builder** —— 构建 `OriginalModel`（6 必填字段；几何可空数组，禁止 null；JSON 中含合法几何时作为 hints 采纳）。
5. **Schema Validation** —— 用 `original_model.schema.json` 校验；失败抛 `ValidationError` 并**立即中止**。
6. **Workspace** —— 保存 `original_model.json`（v1）。
7. **Checkpoint** —— 保存 `checkpoint_parser_v1.json`。
8. **Result** —— 返回统一 `Result`（`next_tasks=["design"]`）。

## 自检
- 输入类型识别正确？
- OriginalModel 6 字段齐全且无 null？
- Schema 校验通过？
- Workspace / Checkpoint 均已落盘？
- `next_tasks` 含 `"design"`？
