#!/bin/bash
# 设置复盘报告上传路径环境变量（服务器端执行）
# 四地域分别配置 EHS_REPORT_BASE + EHS_REGION

set -e

BASE="/root/EHS_docs/documents/异常事件复盘"

echo "=== 配置复盘报告路径 ==="
echo "基础目录: $BASE"
echo ""

# 深圳
echo "[1/4] 深圳 ehs-dashboard.service ..."
cat > /etc/systemd/system/ehs-dashboard.service <<'EOF'
[Unit]
Description=EHS Dashboard (Python Backend)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/EHS_Dashboard/backend
Environment="PATH=/root/EHS_Dashboard/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="EHS_REPORT_BASE=/root/EHS_docs/documents/异常事件复盘"
Environment="EHS_REGION=深圳"
ExecStart=/root/EHS_Dashboard/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 武汉
echo "[2/4] 武汉 ehs-wuhan.service ..."
cat > /etc/systemd/system/ehs-wuhan.service <<'EOF'
[Unit]
Description=EHS Dashboard Wuhan (Python Backend)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/EHS_Dashboard_wuhan/backend
Environment="PATH=/root/EHS_Dashboard_wuhan/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="EHS_REPORT_BASE=/root/EHS_docs/documents/异常事件复盘"
Environment="EHS_REGION=武汉"
ExecStart=/root/EHS_Dashboard_wuhan/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 北京
echo "[3/4] 北京 ehs-beijing.service ..."
cat > /etc/systemd/system/ehs-beijing.service <<'EOF'
[Unit]
Description=EHS Dashboard Beijing (Python Backend)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/EHS_Dashboard_beijing/backend
Environment="PATH=/root/EHS_Dashboard_beijing/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="EHS_REPORT_BASE=/root/EHS_docs/documents/异常事件复盘"
Environment="EHS_REGION=北京"
ExecStart=/root/EHS_Dashboard_beijing/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8002
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 上海
echo "[4/4] 上海 ehs-shanghai.service ..."
cat > /etc/systemd/system/ehs-shanghai.service <<'EOF'
[Unit]
Description=EHS Dashboard Shanghai (Python Backend)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/EHS_Dashboard_shanghai/backend
Environment="PATH=/root/EHS_Dashboard_shanghai/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="EHS_REPORT_BASE=/root/EHS_docs/documents/异常事件复盘"
Environment="EHS_REGION=上海"
ExecStart=/root/EHS_Dashboard_shanghai/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8003
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 重载 & 重启
echo ""
echo "[5/5] 重载 systemd & 重启服务..."
systemctl daemon-reload
systemctl restart ehs-dashboard.service ehs-wuhan.service ehs-beijing.service ehs-shanghai.service

echo ""
echo "=== 完成 ==="
systemctl status ehs-dashboard.service ehs-wuhan.service ehs-beijing.service ehs-shanghai.service --no-pager || true
