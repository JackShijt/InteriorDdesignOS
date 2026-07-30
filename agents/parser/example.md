# Parser Agent - Example

## 示例（来自 scripts/demo_parser.py）

**输入**：`examples/input/sample_json/sample.json`（合法 OriginalModel JSON）

**处理**：
1. Loader 加载，Detector 识别为 `TEXT`。
2. Normalizer 生成 `InputContext`。
3. 因 JSON 含合法几何，作为 hints 采纳，`has_geo=True`。
4. Model Builder 生成 OriginalModel；Schema 校验通过。
5. 落盘 `original_model.json` 与 `checkpoint_parser_v1.json`。

**输出**：
```json
{
  "success": true,
  "output_model": { "metadata": {"project_id": "demo", ...}, "walls": [...], "rooms": [...] },
  "messages": ["输入类型: TEXT"],
  "quality": { "confidence": 0.6, "quality_score": 60, "validation_passed": true },
  "next_tasks": ["design"]
}
```

**多输入识别结果**（demo 第 2 部分）：
| 输入 | 识别 | success |
| --- | --- | --- |
| sample.dwg（占位） | DWG | True |
| sample.pdf（占位） | PDF | True |
| sample.png（占位） | IMAGE | True |
| empty.txt（空） | TEXT | True（几何为空数组） |
