#!/bin/bash
# EHS 安全联锁屏蔽模块重构部署
# 将 Shield 从 Express+React 迁移到 FastAPI+单文件HTML
# 移除 Node.js 依赖，统一架构
set -e

UPDATE_TAR="${1:-ehs-shield-refactor-0601-1406.tar.gz}"

if [ ! -f "$UPDATE_TAR" ]; then
    echo "错误: 找不到更新包 $UPDATE_TAR"
    echo "用法: bash deploy-shield-refactor.sh [更新包路径]"
    exit 1
fi

# 地区配置: 目录名 -> 端口
SITES=(
    "EHS_Dashboard:8000"
    "EHS_Dashboard_wuhan:8001"
    "EHS_Dashboard_beijing:8002"
    "EHS_Dashboard_shanghai:8003"
)

BACKUP_DIR="ehs_backup_$(date +%Y%m%d_%H%M)"
mkdir -p "$BACKUP_DIR"

echo "======================================"
echo "EHS Shield 模块重构部署"
echo "更新包: $UPDATE_TAR"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================"

TMPDIR=$(mktemp -d)
tar xzf "$UPDATE_TAR" -C "$TMPDIR"
UPDATE_SRC="$TMPDIR"

for site in "${SITES[@]}"; do
    DIR=$(echo "$site" | cut -d: -f1)
    PORT=$(echo "$site" | cut -d: -f2)

    if [ ! -d "$DIR" ]; then
        echo "[跳过] 目录不存在: $DIR"
        continue
    fi

    echo ""
    echo ">>> 正在更新 $DIR (端口 $PORT)"

    # 备份关键文件
    cp -r "$DIR/backend/main.py" "$BACKUP_DIR/${DIR##*/}_main.py" 2>/dev/null || true
    mkdir -p "$BACKUP_DIR/${DIR##*/}_shield_frontend"
    cp -r "$DIR/frontend/shield/" "$BACKUP_DIR/${DIR##*/}_shield_frontend/" 2>/dev/null || true

    # 创建新目录
    mkdir -p "$DIR/backend/ehs_shield/api"

    # 拷贝后端
    cp -r "$UPDATE_SRC/backend/ehs_shield/"* "$DIR/backend/ehs_shield/"
    cp "$UPDATE_SRC/backend/main.py" "$DIR/backend/main.py"

    # 拷贝前端
    cp "$UPDATE_SRC/frontend/shield/index.html" "$DIR/frontend/shield/index.html"

    # 删除旧的 React 资产（不再需要）
    rm -rf "$DIR/frontend/shield/assets/" 2>/dev/null || true

    # 停止旧进程（包括可能残留的 Express Shield 进程）
    echo "    停止旧进程..."
    for OLD_PID in $(ps aux | grep "uvicorn.*main:app.*--port $PORT" | grep -v grep | awk '{print $2}'); do
        echo "      停止 uvicorn PID=$OLD_PID"
        kill "$OLD_PID" 2>/dev/null || true
    done
    # 也杀掉旧的 Express Shield 进程（Shield端口: 3456/3457/3458/3459）
    SHIELD_PORT=$((3456 + PORT - 8000))
    for OLD_SHIELD in $(lsof -i :"$SHIELD_PORT" -t 2>/dev/null); do
        echo "      停止旧 Shield Express PID=$OLD_SHIELD (端口 $SHIELD_PORT)"
        kill "$OLD_SHIELD" 2>/dev/null || true
    done
    sleep 2

    # 启动新进程（不再需要 SHIELD_PORT）
    echo "    启动服务 (端口 $PORT)"
    cd "$DIR/backend"
    nohup python3 -m uvicorn main:app --host 0.0.0.0 --port "$PORT" > /tmp/ehs-${DIR##*/}.log 2>&1 &
    cd - > /dev/null
    sleep 2

    echo "    [OK] $DIR 更新完成"
done

rm -rf "$TMPDIR"

echo ""
echo "======================================"
echo "全部更新完成"
echo "备份目录: $BACKUP_DIR"
echo "======================================"
echo ""
echo "检查服务状态:"
for site in "${SITES[@]}"; do
    PORT=$(echo "$site" | cut -d: -f2)
    if lsof -Pi :"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "  端口 $PORT: 运行中"
    else
        echo "  端口 $PORT: 未启动"
    fi
done
echo ""
echo "验证 API:"
for site in "${SITES[@]}"; do
    PORT=$(echo "$site" | cut -d: -f2)
    echo -n "  :$PORT/api/shield/health -> "
    curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/api/shield/health" 2>/dev/null || echo "失败"
done
