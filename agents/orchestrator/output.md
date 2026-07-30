# Orchestrator Output

## 输出格式

```json
{
  "project_id": "Project_001",
  "status": "completed",
  "stages": [
    {"stage": "parse", "status": "completed", "agent": "parser"},
    {"stage": "design", "status": "completed", "agent": "design"},
    {"stage": "layout", "status": "completed", "agent": "layout"}
  ],
  "output_files": [
    "workspace/projects/Project_001/output/平面布置图.dwg",
    "workspace/projects/Project_001/output/电气平面图.dwg"
  ],
  "summary": "设计完成，共生成 8 张图纸"
}
```
