#!/bin/bash
# 直接 patch incidents.py 默认路径 - 武汉
set -e
cd /root/EHS_Dashboard_wuhan/backend/ehs_incident/api
cp incidents.py incidents.py.bak.$(date +%Y%m%d%H%M%S)
sed -i 's|os.getenv("EHS_REPORT_BASE", os.path.join(BASE_DIR, "uploads", "incident"))|"/root/EHS_docs/documents/异常事件复盘"|' incidents.py
sed -i 's|os.getenv("EHS_REGION", "")|"武汉"|' incidents.py
echo "武汉: 已 patch"
grep -n 'REPORT_BASE\|REPORT_DIR' incidents.py | head -5
systemctl restart ehs-wuhan.service
