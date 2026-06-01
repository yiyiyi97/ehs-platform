# EHS 工业安全管理平台

> **E**nvironment, **H**ealth & **S**afety — 工业安全管理平台  
> LOTO 锁定管理 / 安全联锁屏蔽 / 隐患风险管控 / 异常事件记录 / 设备校验管理

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-green) ![Frontend](https://img.shields.io/badge/Frontend-Vanilla%20JS-orange)

---

## 📋 模块概览

| 模块 | 说明 | 后端 |
|------|------|------|
| **LOTO 锁定管理** | 设备上锁挂牌，场地拓扑可视化与联动分析 | Python FastAPI |
| **安全联锁屏蔽** | 屏蔽作业申请、冲突检测、台账追踪、版本管理 | Python FastAPI |
| **隐患风险管控** | 全生命周期管理，风险分级、整改闭环、BI 分析 | Python FastAPI |
| **异常事件记录** | 异常事件记录与复盘，报告上传下载、BI 分析 | Python FastAPI |
| **设备校验管理** | 特种设备 & 计量设备校验台账、临期/超期提醒 | Python FastAPI |

---

## 🏗️ 架构

```
┌─────────────────────────────────────────┐
│              FastAPI :8000               │
│           (统一入口，无外部依赖)            │
├──────────┬──────────┬──────────┬─────────┤
│  LOTO    │  Shield  │  Hazard  │Incident │
│          │(FastAPI) │          │         │
└──────────┴──────────┴──────────┴─────────┘
```

纯 Python 架构，所有模块统一使用 FastAPI + 单文件 HTML，不再依赖 Node.js / Express / React。

支持多实例部署（深圳 :8000、武汉 :8001、北京 :8002、上海 :8003），每个实例独立进程与数据库。

---

## 🚀 快速开始

### 本地开发

```bash
pip install -r backend/requirements.txt
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

浏览器打开 `http://localhost:8000`

### 服务器部署

```bash
bash deploy-shield-refactor.sh ehs-shield-refactor-XXXX.tar.gz
```

---

## 🧩 首页看板

- **LOTO 已上锁** — 当前锁定设备数
- **安全联锁屏蔽** — Active 屏蔽项 + 超时未解除数（按版本过滤）
- **隐患统计** — 隐患总数 + 闭环率
- **异常事件统计** — 事件总数 + 复盘率
- **设备校验** — 临期/超期设备数
- **趋势图** — 隐患/事件趋势
- **安全员排班** — 白班/夜班排班表

---

## 📦 项目结构

```
ehs-platform/
├── backend/
│   ├── main.py                 # 统一入口（注册所有模块路由）
│   ├── requirements.txt
│   ├── ehs_loto/               # LOTO 模块
│   ├── ehs_shield/             # 安全联锁屏蔽（FastAPI）
│   │   ├── models.py           # 数据库模型
│   │   ├── api/
│   │   │   ├── items.py        # 联锁项 CRUD + Excel 导入
│   │   │   ├── applications.py # 申请管理 + 台账 + 历史
│   │   │   ├── stats.py        # 统计
│   │   │   └── push.py         # WeLink 推送
│   │   └── main.py
│   ├── ehs_hazard/             # 隐患模块
│   ├── ehs_incident/           # 异常事件模块
│   └── ehs_equipment/          # 设备校验模块
├── frontend/
│   ├── index.html              # 首页看板
│   ├── loto/                   # LOTO 前端
│   ├── shield/index.html       # 安全联锁屏蔽（单文件）
│   ├── hazard/                 # 隐患前端
│   ├── incident/               # 异常事件前端
│   └── equipment/              # 设备校验前端
├── shield_backend/
│   └── data.db                 # Shield SQLite 数据库（由 FastAPI 直接管理）
├── uploads/                    # 上传文件
├── deploy-shield-refactor.sh   # 部署脚本
└── .gitignore
```

---

## 📡 API 一览

### Shield (`/api/shield/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/shield/applications` | 申请清单（支持 `?version=` 过滤） |
| POST | `/api/shield/applications` | 创建申请（支持文件上传） |
| GET | `/api/shield/applications/{id}/items` | 申请项详情 |
| POST | `/api/shield/applications/{id}/complete` | 完成作业（支持 dry_run 冲突检测） |
| PUT | `/api/shield/applications/{id}/extend` | 延期恢复时间 |
| DELETE | `/api/shield/applications/{id}` | 删除申请 |
| GET | `/api/shield/ledger` | 台账（超时优先，支持 `?version=` 过滤） |
| GET | `/api/shield/history` | 历史记录（支持 `?version=` 过滤） |
| GET | `/api/shield/stats` | 统计（Active + 超时数） |
| GET | `/api/shield/items` | 联锁项清单（支持 `?version=` 过滤） |
| POST | `/api/shield/items` | 新增联锁项 |
| PUT | `/api/shield/items/{id}` | 编辑联锁项 |
| DELETE | `/api/shield/items/{id}` | 删除联锁项 |
| POST | `/api/shield/items/import` | 批量导入联锁项（JSON 或 Excel） |
| GET | `/api/shield/versions` | 版本列表 |
| POST | `/api/shield/versions` | 新增版本 |
| POST | `/api/shield/push/welink-daily` | WeLink 日报推送 |

### 其他模块

| 模块 | 前缀 | 说明 |
|------|------|------|
| LOTO | `/api/loto/` | 设备 CRUD、连接管理、场地拓扑 |
| Hazard | `/api/hazard/` | 隐患 CRUD、统计、趋势、Excel 导入导出 |
| Incident | `/api/incident/` | 事件 CRUD、统计、报告上传下载 |
| Equipment | `/api/equipment/` | 设备校验台账、Excel 导入导出 |
| 排班 | `/api/safety-officer` | 安全员排班查询与保存 |

---

## 🗃️ 数据存储

各模块使用独立 SQLite 数据库：

| 数据库 | 位置 | 模块 |
|--------|------|------|
| `loto.db` | `backend/data/` | LOTO |
| `hazard.db` | `backend/data/` | Hazard |
| `incident.db` | `backend/data/` | Incident |
| `equipment.db` | `backend/data/` | Equipment |
| `data.db` | `shield_backend/` | Shield |
| `safety_officer.json` | `data/` | 安全员排班 |

---

## 🔧 运维

```bash
# 查看服务状态
lsof -i :8000

# 重启
kill $(lsof -i :8000 -t) && python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
```
