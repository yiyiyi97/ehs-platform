#!/bin/bash
# EHS incident 填写位置字段更新 — 服务器端部署脚本
# 用法：将 incident-location-update.tar.gz 上传到 /root/，然后运行此脚本

set -e

PKG="/root/incident-location-update.tar.gz"
PROJECT="/root/EHS_Dashboard"
BACKUP="/root/ehs-backup-$(date +%Y%m%d-%H%M%S)"

if [ ! -f "$PKG" ]; then
  echo "错误：找不到 $PKG"
  echo "请先将 incident-location-update.tar.gz 上传到服务器 /root/ 目录"
  exit 1
fi

echo "=== EHS 异常事件填写位置字段更新 ==="
echo "备份目录: $BACKUP"

# 1. 备份
echo "[1/3] 备份现有文件..."
mkdir -p "$BACKUP"
cp "$PROJECT/backend/ehs_incident/models.py" "$BACKUP/" 2>/dev/null || true
cp "$PROJECT/backend/ehs_incident/api/incidents.py" "$BACKUP/" 2>/dev/null || true
cp "$PROJECT/frontend/incident/index.html" "$BACKUP/" 2>/dev/null || true

# 2. 解压更新
echo "[2/3] 应用更新..."
cd "$PROJECT"
tar -xzf "$PKG" --overwrite

# 3. 重启服务
echo "[3/3] 重启 EHS Dashboard 服务..."
systemctl restart ehs-dashboard.service
sleep 2
systemctl status ehs-dashboard.service --no-pager || true

echo ""
echo "=== 部署完成 ==="
echo "备份: $BACKUP"
echo ""
echo "验证步骤："
echo "  1. 打开 http://10.29.113.101:8000/incident/"
echo "  2. 点击「新增事件」→ 确认「填写位置」下拉框存在"
echo "  3. 打开「选项管理」→ 给「填写位置」添加几个选项"
echo "  4. 回到新增事件表单 → 确认选项已加载"
