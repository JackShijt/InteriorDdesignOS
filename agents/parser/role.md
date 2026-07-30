# Parser Agent

## 角色
系统入口 Agent（Phase 3 · v1.0）。负责把**原始输入**（DWG / DXF / PDF / 图片 / 用户 JSON / TXT / ZIP）解析为统一数据模型 **OriginalModel**，是整条 InteriorDesignOS 流水线的第一环。

## 职责
- 识别输入类型（`InputType`：DWG / DXF / PDF / IMAGE / TEXT / ZIP / UNKNOWN）。
- 加载文件元数据（存在性、大小、sha256 Hash、MIME），**不做业务解析**。
- 归一化为统一 `InputContext`。
- 构建 `OriginalModel`（6 必填字段，几何不可解析时为空数组，**禁止 null**）。
- 用 `original_model.schema.json` 做 Schema 校验，失败即中止。
- 落盘 Workspace（`original_model.json` v1）与 Checkpoint（`checkpoint_parser_v1.json`）。
- 返回统一 `Result`（`next_tasks=["design"]`），由 Orchestrator / Dispatcher 调度下游。

## 不负责（§14/§15）
- 不负责设计、布局、CAD 绘图、几何修复、渲染、导出等下游工作。
- 禁止 AutoCAD MCP、CAD 绘图、LLM 推理、装修算法。
