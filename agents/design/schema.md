# Design Agent · Schema（数据契约）

## DesignSpec（`schemas/design/design_spec.schema.json`）
必填字段（§1）：
`metadata`, `version`, `design_goal`, `style`, `budget`, `family`,
`rooms`, `constraints`, `preferences`, `materials`, `lighting`, `storage`, `special_requirements`。

- `style.labels`：枚举 `Modern/Minimal/Nordic/Japanese/Industrial/Chinese/Luxury/Mixed`，至少 1 个（§5）。
- `budget.level`：枚举 `LOW/MEDIUM/HIGH/PREMIUM`（§6）。
- `family`：`adults/children/elders/pets/work_from_home/accessibility`（§7）。
- `materials[].brand_recommended`：必须为 `false`（禁止品牌推荐，§8）。
- `metadata`：`$ref` 指向 `core/metadata.schema.json`（PROJECT_RULES §4.3）。
- `additionalProperties: false` ⇒ **禁止** 出现 `CAD/Geometry/Drawing/Layer/Entity/DWG` 等字段（§17）。

## 引用
- `core/metadata.schema.json`
- `core/task.schema.json`（任务状态）
- `project/project.schema.json`（Project 含 `DESIGN_SPEC` 阶段）

校验器：`agents/design/validator.py`（复用 `referencing` 全局 `$ref` 注册表，与各 schema 互引一致）。
