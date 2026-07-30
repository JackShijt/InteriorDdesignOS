# Design Agent · Output（输出结构）

统一返回 `Result`（见 `runtime/message.Result`）：

```python
Result(
    success=True,
    output_model=<DesignSpec dict>,     # 通过 design_spec.schema.json 校验
    messages=["DesignSpec 已生成并通过校验"],
    quality={"confidence": float, "quality_score": int, "validation_passed": True},
    next_tasks=[],                       # 不自动触发下游（Layout 阶段未进入）
)
```

失败（如缺少 OriginalModel、Schema 校验不通过）时返回 `Result(success=False, messages=[错误])`，不抛异常（框架安全）。

落盘：
- `workspace/projects/<project_id>/design_spec.json`（v1）
- `workspace/projects/<project_id>/checkpoint_design_v1.json`
