#!/bin/bash
# EHS incident 表单下拉框更新 — 批量部署脚本
# 用法：修改 SERVER_LIST，然后执行此脚本

set -e

# ── 配置 ──
PKG="/root/incident-form-dropdown-all.tar.gz"
REMOTE_DIR="/root/EHS_Dashboard"

# 填入所有地域服务器，示例：
# SERVER_LIST=(
#   "root@10.29.113.101"
#   "root@10.29.113.102"
#   "root@192.168.1.100"
# )
SERVER_LIST=(
  "root@10.29.113.101"
)

# ── 检查 ──
if [ ! -f "$PKG" ]; then
  echo "错误：找不到 $PKG"
  echo "请先将 incident-form-dropdown-all.tar.gz 上传到本机 /root/"
  exit 1
fi

# ── 逐台部署 ──
for SERVER in "${SERVER_LIST[@]}"; do
  echo ""
  echo "========================================"
  echo "正在部署到: $SERVER"
  echo "========================================"

  # 1. 上传
  echo "[1/4] 上传..."
  scp "$PKG" "$SERVER:$PKG"

  # 2. 服务器端执行
  echo "[2/4] 备份 & 解压..."
  ssh "$SERVER" bash <<EOF
    set -e
    BACKUP="/root/ehs-backup-\$(date +%Y%m%d-%H%M%S)"
    mkdir -p \$BACKUP
    cp "$REMOTE_DIR/backend/ehs_incident/models.py" \$BACKUP/ 2>/dev/null || true
    cp "$REMOTE_DIR/backend/ehs_incident/api/incidents.py" \$BACKUP/ 2>/dev/null || true
    cp "$REMOTE_DIR/frontend/incident/index.html" \$BACKUP/ 2>/dev/null || true
    cd "$REMOTE_DIR"
    tar -xzf "$PKG" --overwrite
    echo "备份完成: \$BACKUP"
EOF

  # 3. 重启
  echo "[3/4] 重启服务..."
  ssh "$SERVER" "systemctl restart ehs-dashboard.service; sleep 2; systemctl status ehs-dashboard.service --no-pager || true"

  echo "[4/4] $SERVER 部署完成"
done

echo ""
echo "========================================"
echo "全部地域部署完成"
echo "========================================"
