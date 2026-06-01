#!/bin/bash
# 清理所有 uvicorn 进程并重新启动（含 Shield 端口隔离）

echo "=== 停止所有 uvicorn 进程 ==="
for pid in $(ps aux | grep "uvicorn.*main:app" | grep -v grep | awk '{print $2}'); do
    echo "  杀掉 PID=$pid"
    kill -9 "$pid" 2>/dev/null || true
done

sleep 2

echo ""
echo "=== 验证端口已释放 ==="
for port in 8000 8001 8002 8003; do
    if ss -tlnp | grep -q ":$port "; then
        echo "  端口 $port 仍被占用！"
    else
        echo "  端口 $port 已释放"
    fi
done

echo ""
echo "=== 重新启动各地域服务 ==="

# 深圳 8000 (Shield 3456)
cd ~/EHS_Dashboard/backend
nohup env SHIELD_PORT="3456" /root/EHS_Dashboard/.venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/ehs-EHS_Dashboard.log 2>&1 &
echo "  深圳 (8000, Shield 3456) 已启动"

# 武汉 8001 (Shield 3457)
cd ~/EHS_Dashboard_wuhan/backend
nohup env SHIELD_PORT="3457" /root/yt_env/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 > /tmp/ehs-EHS_Dashboard_wuhan.log 2>&1 &
echo "  武汉 (8001, Shield 3457) 已启动"

# 北京 8002 (Shield 3458)
cd ~/EHS_Dashboard_beijing/backend
nohup env SHIELD_PORT="3458" /root/yt_env/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8002 > /tmp/ehs-EHS_Dashboard_beijing.log 2>&1 &
echo "  北京 (8002, Shield 3458) 已启动"

# 上海 8003 (Shield 3459)
cd ~/EHS_Dashboard_shanghai/backend
nohup env SHIELD_PORT="3459" /root/yt_env/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8003 > /tmp/ehs-EHS_Dashboard_shanghai.log 2>&1 &
echo "  上海 (8003, Shield 3459) 已启动"

sleep 3

echo ""
echo "=== 检查服务状态 ==="
ps aux | grep uvicorn | grep -v grep
