#!/bin/bash
# 直接 patch incidents.py 默认路径 - 北京
set -e
cd /root/EHS_Dashboard_beijing/backend/ehs_incident/api
cp incidents.py incidents.py.bak.$(date +%Y%m%d%H%M%S)
sed -i 's|os.getenv("EHS_REPORT_BASE", os.path.join(BASE_DIR, "uploads", "incident"))|"/root/EHS_docs/documents/异常事件复盘"|' incidents.py
sed -i 's|os.getenv("EHS_REGION", "")|"北京"|' incidents.py
echo "北京: 已 patch"
grep -n 'REPORT_BASE\|REPORT_DIR' incidents.py | head -5
systemctl restart ehs-beijing.service
