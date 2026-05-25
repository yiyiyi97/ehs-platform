# 异常事件记录子系统 (Incident Management)

异常事件记录是 EHS 工业安全管理平台下的一个子系统，用于记录、追踪和分析实验室异常事件，支持复盘报告上传下载、BI 数据分析、Excel 导入导出。

## 目录结构

```
ehs-platform/
├── backend/
│   ├── main.py                      # 统一 FastAPI 入口，注册 incident 路由
│   └── ehs_incident/
│       ├── __init__.py
│       ├── main.py                  # 核心路由（占位）
│       ├── models.py                # SQLAlchemy 数据模型
│       └── api/
│           ├── __init__.py
│           ├── auth.py              # 复用 ehs_hazard 认证
│           ├── incidents.py         # 异常事件 CRUD + 复盘报告上传下载
│           ├── stats.py             # BI 统计 API
│           ├── options.py           # 字段选项管理 API
│           └── excel.py             # Excel 导入导出 + 模板下载
├── frontend/
│   └── incident/
│       └── index.html               # 单页应用（清单/表单/BI/选项管理）
├── data/
│   └── incident.db                  # SQLite 数据库
└── uploads/
    └── incident/                    # 复盘报告上传目录
```

## 数据库模型

### incidents 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 自增主键 |
| incident_no | String | 事件单号（自动生成：YYYYMMDD+实验室+序号） |
| incident_type | String | 异常类型 |
| event_level | String | 事件等级（High/Medium/Low） |
| lab | String | 实验室 |
| version | String | 版本 |
| subsystem | String | 子系统 |
| device_name | String | 设备名称 |
| description | Text | 异常描述 |
| review_report_path | String | 复盘报告文件名（uuid） |
| status | String | 状态：待复盘 / 已复盘 / 措施已落实 |
| reporter | String | 报告人 |
| report_date | String | 报告日期（YYYY-MM-DD） |
| review_date | String | 复盘日期（YYYY-MM-DD） |
| reviewer | String | 复盘人（上传报告时自动记录） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### incident_options 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 自增主键 |
| field_name | String | 字段名 |
| value | String | 选项值 |
| created_at | DateTime | 创建时间 |

## API 接口

### 异常事件管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/incident/incidents` | 事件清单（分页、筛选、排序、搜索） |
| GET | `/api/incident/incidents/{id}` | 单条事件详情 |
| POST | `/api/incident/incidents` | 创建事件（自动生单号） |
| PUT | `/api/incident/incidents/{id}` | 更新事件 |
| DELETE | `/api/incident/incidents/{id}` | 删除事件（同时删文件） |
| POST | `/api/incident/incidents/{id}/upload` | 上传复盘报告（自动设状态为已复盘） |
| GET | `/api/incident/incidents/{id}/download` | 下载复盘报告 |

### 选项管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/incident/options/fields` | 获取所有字段选项 |
| GET | `/api/incident/options?field=` | 查询选项列表 |
| POST | `/api/incident/options` | 添加选项 |
| DELETE | `/api/incident/options/{id}` | 删除选项 |

### Excel 导入导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/incident/excel/export/excel` | 导出 Excel |
| POST | `/api/incident/excel/import/excel` | 导入 Excel（自动提取选项） |
| GET | `/api/incident/excel/export/template` | 下载空白导入模板 |

### BI 统计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/incident/stats/summary` | 总览统计 |
| GET | `/api/incident/stats/aggregate?group_by=` | 分组聚合 |
| GET | `/api/incident/stats/trend` | 事件趋势 |
| GET | `/api/incident/stats/cross` | 交叉分析 |
| GET | `/api/incident/stats/trend-lab` | 按实验室趋势 |

## 前端页面

访问地址：`http://localhost:8000/incident/`

### 功能模块

1. **事件清单**
   - 筛选：状态、异常类型、事件等级、实验室、版本、子系统
   - 搜索：单号、描述、设备名称
   - 排序：提交时间 / 复盘时间（升序/降序）
   - 分页：每页 30 条
   - 操作列：编辑、上传报告、标记措施已落实、删除（管理员）
   - 复盘报告：已上传可点击下载

2. **新增/编辑**
   - 表单字段：异常类型、事件等级、实验室、版本、子系统、设备名称、异常描述、状态、报告人、报告日期、复盘日期、复盘报告上传
   - 事件单号自动生成
   - 编辑时显示当前复盘报告并可更换

3. **BI 分析**
   - 总览卡片：事件总数、待处理、已闭环、已复盘、闭环率
   - 主图分布：支持柱状/饼图/折线图等，可按各字段分组
   - 趋势分析：近 7/30/90/180/365 天
   - 实验室趋势：堆叠面积/折线图
   - 交叉分析：双维度堆叠柱状图

4. **顶部操作栏**
   - 导入 Excel、导出 Excel、下载模板、选项管理（管理员）

## 部署说明

统一后端由 `backend/main.py` 统一管理，incident 路由在启动时自动注册。

```bash
cd /Users/heyi/ehs-platform
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

前端静态文件通过 FastAPI `StaticFiles` 挂载在 `/incident/` 路径。

数据库在首次启动时自动创建（`init_db()`），文件上传目录 `uploads/incident/` 需在服务启动前确保存在。
