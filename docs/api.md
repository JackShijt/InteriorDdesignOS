# API

## API 接口

### 项目接口
- `POST /api/projects` - 创建项目
- `GET /api/projects/:id` - 获取项目
- `DELETE /api/projects/:id` - 删除项目

### 设计接口
- `POST /api/projects/:id/generate` - 生成设计
- `GET /api/projects/:id/status` - 获取进度

### 导出接口
- `POST /api/projects/:id/export` - 导出图纸
- `GET /api/projects/:id/download` - 下载成果
