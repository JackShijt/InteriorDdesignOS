# Parser Agent - Checklist

## 自检清单
- [ ] 输入文件存在且被识别为已知 `InputType`（否则 UNKNOWN 但流程继续）
- [ ] `InputContext` 已归一化（路径 / 编码 / 单位 / 坐标 / 文件名）
- [ ] `OriginalModel` 6 个必填顶层键齐全，几何为数组（可为空），**无 null**
- [ ] 通过 `original_model.schema.json` 校验（`validation_passed=true`）
- [ ] `workspace/projects/<id>/original_model.json` 已落盘（v1）
- [ ] `workspace/projects/<id>/checkpoint_parser_v1.json` 已落盘
- [ ] 返回统一 `Result`，`next_tasks` 含 `"design"`
- [ ] 全程使用统一日志（ISO8601），无 `print` / `sys.exit`
- [ ] 异常统一为 `RecoverableError` / `ValidationError` / `FatalError`
- [ ] 未调用 CAD 工具 / LLM / 任何设计类 Agent（§15）
