# EHS 工业安全管理平台

> **E**nvironment, **H**ealth & **S**afety — 工业安全管理平台  
> LOTO 锁定管理 / 安全联锁屏蔽 / 隐患风险管控 / 异常事件记录  
> 面向 EHS 同行的开源工具

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-green) ![Vue.js](https://img.shields.io/badge/Frontend-Vanilla%20JS-orange) ![Node.js](https://img.shields.io/badge/Shield-Express.js-black)

---

## 📋 模块概览

| 模块 | 说明 | 前端 | 后端 |
|------|------|------|------|
| **LOTO 锁定管理** | 设备上锁挂牌，场地拓扑可视化与联动分析 | `/loto/` | Python FastAPI |
| **安全联锁屏蔽** | 屏蔽作业申请审批、冲突检测、台账追踪 | `/shield/` (React SPA) | Node.js Express |
| **隐患风险管控** | 全生命周期管理，风险分级、整改闭环、BI 分析 | `/hazard/` | Python FastAPI |
| **异常事件记录** | 异常事件记录与复盘，报告上传下载、BI 分析 | `/incident/` | Python FastAPI |
| **EHS 公档** | 公共文档资料库 | 外部 FileBrowser (:8090) | — |

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx / 反向代理                       │
└──────────┬──────────────────────────────┬───────────────┘
           │                              │
    ┌──────▼──────┐              ┌───────▼────────┐
    │  FastAPI    │              │  Express.js    │
    │  :8000      │  proxy ───►  │  :3456         │
    │  (Python)   │              │  (Shield)      │
    └──┬───┬───┬──┘              └────────────────┘
       │   │   │
  ┌────┘   │   └──────┐
  ▼        ▼           ▼
LOTO    Hazard   Incident
```

支持多实例部署，每个实例独立进程与数据库。

---

## 🚀 快速开始

### 本地开发

```bash
# 依赖
pip install -r backend/requirements.txt
cd shield_backend && npm install && cd ..

# 启动
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

浏览器打开 `http://localhost:8000`

### 服务器部署

```bash
# 一键部署
bash deploy.sh

# 或手动 rsync 到服务器
rsync -avz --delete \
  --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='shield_backend/node_modules' --exclude='shield_backend/src' \
  --exclude='data/*.db' --exclude='uploads/*' \
  ./ user@your-server:/path/to/EHS_Dashboard/
```

---

## 🧩 首页看板

首页展示全局数据概览：

- **LOTO 已上锁** — 当前锁定设备数
- **安全联锁屏蔽** — Active 屏蔽项 + 超时未解除数
- **隐患统计** — 隐患总数 + 闭环率
- **异常事件统计** — 事件总数 + 复盘率
- **隐患/事件趋势图** — 按天/周/月
- **今日安全员排班** — 白班/夜班排班表，支持手动编辑保存

---

## 📦 项目结构

```
ehs-platform/
├── backend/
│   ├── main.py                 # 统一入口（注册所有模块路由 + Shield proxy）
│   ├── requirements.txt        # Python 依赖
│   ├── data/                   # SQLite 数据库（gitignored）
│   ├── ehs_loto/               # LOTO 模块
│   ├── ehs_hazard/             # 隐患模块
│   ├── ehs_incident/           # 异常事件模块
│   └── uploads/                # 上传文件
├── frontend/
│   ├── index.html              # 首页看板
│   ├── index-light.html        # 浅色主题版
│   ├── loto/                   # LOTO 前端
│   ├── hazard/                 # 隐患前端
│   ├── incident/               # 异常事件前端
│   └── shield/                 # 安全联锁屏蔽 SPA（React 构建产物）
├── shield_backend/
│   ├── src/                    # TypeScript 源码
│   ├── dist/                   # 编译产物
│   ├── package.json
│   └── tsconfig.json
├── wheels/                     # ARM64 Python wheels（服务器离线安装用）
├── deploy.sh                   # 服务器一键部署
├── start.sh                    # 本地启动
└── .gitignore
```

---

## 📡 API 一览

### LOTO (`/api/loto/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/loto/export` | 导出设备清单 |
| GET | `/api/loto/sites` | 场地列表 |
| GET | `/api/loto/devices/` | 设备 CRUD |
| GET | `/api/loto/connections/` | 连接关系 CRUD |

### Shield (`/api/shield/` → Express :3456)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/shield/applications` | 屏蔽申请清单 |
| POST | `/api/shield/applications` | 创建申请 |
| GET | `/api/shield/applications/{id}/items` | 申请项详情 |
| POST | `/api/shield/applications/{id}/complete` | 完成作业 |
| GET | `/api/shield/ledger` | 台账（按超时排序） |
| GET | `/api/shield/history` | 历史记录 |
| GET | `/api/shield/stats` | 统计（Active + 超时数） |
| GET | `/api/shield/versions` | 版本管理 |
| GET | `/api/shield/shield-items` | 屏蔽项 CRUD |

### Hazard (`/api/hazard/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/hazard/hazards` | 隐患 CRUD + 分页/筛选/排序 |
| GET | `/api/hazard/stats/summary` | 总览统计 |
| GET | `/api/hazard/stats/trend` | 趋势分析 |
| GET | `/api/hazard/stats/aggregate` | 分组聚合 |
| GET | `/api/hazard/stats/cross` | 交叉分析 |
| GET | `/api/hazard/excel/export` | Excel 导出 |
| POST | `/api/hazard/excel/import` | Excel 导入 |

### Incident (`/api/incident/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/incident/incidents` | 事件 CRUD + 分页/筛选 |
| POST | `/api/incident/incidents/{id}/upload` | 复盘报告上传 |
| GET | `/api/incident/incidents/{id}/download` | 复盘报告下载 |
| GET | `/api/incident/stats/trend` | 趋势分析 |
| GET | `/api/incident/excel/export` | Excel 导出 |

### 安全员排班 (`/api/safety-officer`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/safety-officer?date=` | 获取排班（默认今天） |
| POST | `/api/safety-officer` | 保存排班（JSON body） |

---

## 🗃️ 数据存储

各模块使用独立 SQLite 数据库，存于 `backend/data/`：

- `loto.db` — LOTO 设备与连接
- `hazard.db` — 隐患记录
- `incident.db` — 异常事件
- `safety_officer.json` — 安全员排班（JSON）

Shield 模块使用独立 SQLite 数据库 `shield_backend/data.db`（由 Express 管理）。

---

## 🔧 运维

### 服务管理

```bash
systemctl status ehs-dashboard
systemctl restart ehs-dashboard
```

### 心跳检测

`/api/shield/stats` 返回 shield 后端状态，如返回 `{"error":"Shield backend unavailable"}` 说明 Express 进程未启动。

---

## 🔐 认证

内网环境使用简化认证（stub），无需登录即可访问。  
LOTO/Shield 默认无认证，Hazard/Incident 支持基于 localStorage Token 的鉴权。

---


