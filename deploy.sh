#!/bin/bash
set -e

# EHS Dashboard — 部署脚本
# 服务器: 10.29.113.101 (内网地址，需在局域网内执行)

SERVER="root@10.29.113.101"
REMOTE_DIR="/root/EHS_Dashboard"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== EHS Dashboard 部署 ==="
echo "服务器:   $SERVER"
echo "远程目录: $REMOTE_DIR"
echo "本地目录: $LOCAL_DIR"
echo ""

# ── 1. Rsync ──
echo "[1/3] 同步文件到服务器..."
rsync -avz --delete \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='shield_backend/node_modules' \
  --exclude='shield_backend/src' \
  --exclude='data/*.db' \
  --exclude='data/*.db-shm' \
  --exclude='data/*.db-wal' \
  --exclude='uploads/*' \
  --exclude='*.log' \
  "$LOCAL_DIR/" "$SERVER:$REMOTE_DIR/"

# ── 2. 服务端安装 ──
echo ""
echo "[2/3] 服务器安装依赖..."
ssh "$SERVER" bash <<'EOF'
  set -e
  cd /root/EHS_Dashboard

  # Python venv + 依赖（使用内部镜像源）
  python3 -m venv .venv
  source .venv/bin/activate
  pip config set global.index-url https://mirrors-codeartsx-cn-southwest-2.sicarrier.com/pypi/simple
  pip config set global.trusted-host mirrors-codeartsx-cn-southwest-2.sicarrier.com
  pip config set global.timeout 120
  pip install -q -r backend/requirements.txt

  # Node.js 依赖
  cd shield_backend
  npm install --production -q 2>/dev/null || echo "⚠️ npm install 跳过（可手动执行）"
  cd ..

  # 数据目录
  mkdir -p data uploads shield_backend/uploads

  # systemd 服务
  cat > /etc/systemd/system/ehs-dashboard.service <<'EOFSVC'
[Unit]
Description=EHS Dashboard
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/root/EHS_Dashboard/backend
Environment="PATH=/root/EHS_Dashboard/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/root/EHS_Dashboard/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOFSVC
  systemctl daemon-reload
  systemctl enable ehs-dashboard.service 2>/dev/null || true
EOF

# ── 3. 启动 ──
echo ""
echo "[3/3] 启动服务..."
ssh "$SERVER" "systemctl restart ehs-dashboard.service; sleep 2; systemctl status ehs-dashboard.service --no-pager || true"

echo ""
echo "=== 部署完成 ==="
echo "Dashboard: http://10.29.113.101:8000/"
echo "LOTO:      http://10.29.113.101:8000/loto/"
echo "Shield:    http://10.29.113.101:8000/shield/"
echo "Hazard:    http://10.29.113.101:8000/hazard/"
