#!/bin/bash
# 一次性配置所有地域复盘报告上传路径
# 服务器端直接执行

set -e

BASE="/root/EHS_docs/documents/异常事件复盘"

echo "=== 配置复盘报告路径 ==="
echo "基础目录: $BASE"
echo ""

# 深圳
systemctl cat ehs-dashboard.service 2>/dev/null | sed \
  -e '/^ExecStart=/i Environment="EHS_REPORT_BASE=/root/EHS_docs/documents/异常事件复盘"\nEnvironment="EHS_REGION=深圳"' \
  -e '/^Environment="EHS_REPORT_BASE/d' -e '/^Environment="EHS_REGION/d' \
  > /tmp/ehs-dashboard.service.new && mv /tmp/ehs-dashboard.service.new /etc/systemd/system/ehs-dashboard.service
echo "[1/4] 深圳 ehs-dashboard.service ✓"

# 武汉
systemctl cat ehs-wuhan.service 2>/dev/null | sed \
  -e '/^ExecStart=/i Environment="EHS_REPORT_BASE=/root/EHS_docs/documents/异常事件复盘"\nEnvironment="EHS_REGION=武汉"' \
  -e '/^Environment="EHS_REPORT_BASE/d' -e '/^Environment="EHS_REGION/d' \
  > /tmp/ehs-wuhan.service.new && mv /tmp/ehs-wuhan.service.new /etc/systemd/system/ehs-wuhan.service
echo "[2/4] 武汉 ehs-wuhan.service ✓"

# 北京
systemctl cat ehs-beijing.service 2>/dev/null | sed \
  -e '/^ExecStart=/i Environment="EHS_REPORT_BASE=/root/EHS_docs/documents/异常事件复盘"\nEnvironment="EHS_REGION=北京"' \
  -e '/^Environment="EHS_REPORT_BASE/d' -e '/^Environment="EHS_REGION/d' \
  > /tmp/ehs-beijing.service.new && mv /tmp/ehs-beijing.service.new /etc/systemd/system/ehs-beijing.service
echo "[3/4] 北京 ehs-beijing.service ✓"

# 上海
systemctl cat ehs-shanghai.service 2>/dev/null | sed \
  -e '/^ExecStart=/i Environment="EHS_REPORT_BASE=/root/EHS_docs/documents/异常事件复盘"\nEnvironment="EHS_REGION=上海"' \
  -e '/^Environment="EHS_REPORT_BASE/d' -e '/^Environment="EHS_REGION/d' \
  > /tmp/ehs-shanghai.service.new && mv /tmp/ehs-shanghai.service.new /etc/systemd/system/ehs-shanghai.service
echo "[4/4] 上海 ehs-shanghai.service ✓"

# 重载 & 重启
echo ""
systemctl daemon-reload
systemctl restart ehs-dashboard.service ehs-wuhan.service ehs-beijing.service ehs-shanghai.service
echo ""
echo "=== 全部完成 ==="
systemctl status ehs-dashboard.service ehs-wuhan.service ehs-beijing.service ehs-shanghai.service --no-pager || true
