# Design Agent · Input（输入契约）

Design Agent 由 `Dispatcher` 经 `AgentContext` 调度（`run(context)`）：

| 来源 | 字段 | 说明 |
|------|------|------|
| `context.parameters.requirement` | str | 用户自然语言需求（可空，空则使用缺省假设） |
| `context.parameters.original_model_path` | str(path) | 可选，直接指定 OriginalModel |
| `context.input_refs` | [path] | 可选 `.json` 指向 OriginalModel，或 `.txt`/`.md` 指向需求文件 |
| 回退 | `workspace/projects/<pid>/original_model.json` | 默认从同项目 Workspace 读取 Parser 产出 |

`OriginalModel` 数据契约见 `schemas/cad/original_model.schema.json`。
