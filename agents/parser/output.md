# Parser Agent - Output

## 返回结构
统一 `Result`（**禁止返回裸 dict**）：

```json
{
  "success": true,
  "output_model": { "metadata": {...}, "units": {...}, "coordinates": {...},
                    "walls": [], "doors": [], "windows": [], "rooms": [] },
  "messages": ["输入类型: DWG"],
  "quality": { "confidence": 0.3, "quality_score": 30, "validation_passed": true },
  "next_tasks": ["design"]
}
```

- `success`：布尔。
- `output_model`：`OriginalModel`，恒含 6 个必填顶层键，几何可为空数组。
- `messages`：人类可读消息（含识别到的输入类型）。
- `quality`：占位质量评估，诚实标注低置信度。
- `next_tasks`：固定为 `["design"]`，驱动下游。

## 落盘产物
- `workspace/projects/<project_id>/original_model.json`（v1，OriginalModel 全量）。
- `workspace/projects/<project_id>/checkpoint_parser_v1.json`
  （含 `stage=ORIGINAL_MODEL`、`original_model`、`task_status={"parser":"COMPLETED"}`、`project_status`）。

## 失败表达
框架内（`run`）不直接抛异常，统一以 `Result(success=False, ...)` 返回；
独立运行（`process_file` / `run_parser`）会上抛 `ValidationError` / `FatalError` / `RecoverableError`。
