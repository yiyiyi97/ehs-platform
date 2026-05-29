#!/bin/bash
# 直接 patch incidents.py 默认路径，每台服务器上执行
# 深圳

set -e

cd /root/EHS_Dashboard/backend/ehs_incident/api

# 备份
cp incidents.py incidents.py.bak.$(date +%Y%m%d%H%M%S)

# 把默认路径从 uploads/incident 改成目标路径
sed -i 's|os.getenv("EHS_REPORT_BASE", os.path.join(BASE_DIR, "uploads", "incident"))|"/root/EHS_docs/documents/异常事件复盘"|' incidents.py
sed -i 's|os.getenv("EHS_REGION", "")|"深圳"|' incidents.py

echo "=== 验证修改 ==="
grep -n 'EHS_REPORT_BASE\|EHS_REGION\|REPORT_BASE\|REPORT_DIR' incidents.py

echo ""
echo "=== 重启服务 ==="
systemctl restart ehs-dashboard.service
sleep 1
systemctl status ehs-dashboard.service --no-pager
