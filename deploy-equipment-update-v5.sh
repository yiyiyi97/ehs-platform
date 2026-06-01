#!/bin/bash
# EHS 全模块升级脚本 v6
# 修复：hazard/loto/incident 数据不隔离、equipment 统一 auth
# 适用：深圳/武汉/北京/上海 四个地区实例

set -e

UPDATE_TAR="${1:-ehs-equipment-update-0529-v6.tar.gz}"

if [ ! -f "$UPDATE_TAR" ]; then
    echo "错误: 找不到更新包 $UPDATE_TAR"
    echo "用法: bash deploy-equipment-update-v5.sh [更新包路径]"
    exit 1
fi

# 地区配置: 目录名 -> 端口 -> Shield端口
SITES=(
    "EHS_Dashboard:8000:3456"
    "EHS_Dashboard_wuhan:8001:3457"
    "EHS_Dashboard_beijing:8002:3458"
    "EHS_Dashboard_shanghai:8003:3459"
)

BACKUP_DIR="ehs_backup_$(date +%Y%m%d_%H%M)"
mkdir -p "$BACKUP_DIR"

echo "======================================"
echo "EHS 全模块升级 v6"
echo "更新包: $UPDATE_TAR"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================"

# 先解压到临时目录
TMPDIR=$(mktemp -d)
tar xzf "$UPDATE_TAR" -C "$TMPDIR"
UPDATE_SRC="$TMPDIR"

for site in "${SITES[@]}"; do
    DIR=$(echo "$site" | cut -d: -f1)
    PORT=$(echo "$site" | cut -d: -f2)
    SHIELD_PORT=$(echo "$site" | cut -d: -f3)

    if [ ! -d "$DIR" ]; then
        echo "[跳过] 目录不存在: $DIR"
        continue
    fi

    echo ""
    echo ">>> 正在更新 $DIR (端口 $PORT)"

    # 备份
    cp -r "$DIR" "$BACKUP_DIR/${DIR}_bak" 2>/dev/null || true

    # 删除旧文件
    rm -f "$DIR/backend/ehs_equipment/api/audit.py"

    # 创建目录结构
    mkdir -p "$DIR/backend/ehs_equipment/api"
    mkdir -p "$DIR/backend/ehs_hazard"
    mkdir -p "$DIR/backend/ehs_loto"
    mkdir -p "$DIR/backend/ehs_incident"
    mkdir -p "$DIR/frontend/equipment"
    mkdir -p "$DIR/frontend/hazard"
    mkdir -p "$DIR/frontend/incident"

    # 覆盖后端文件
    cp -r "$UPDATE_SRC/backend/ehs_equipment/"* "$DIR/backend/ehs_equipment/"
    cp -r "$UPDATE_SRC/backend/ehs_hazard/"* "$DIR/backend/ehs_hazard/"
    cp -r "$UPDATE_SRC/backend/ehs_loto/"* "$DIR/backend/ehs_loto/"
    cp -r "$UPDATE_SRC/backend/ehs_incident/"* "$DIR/backend/ehs_incident/"
    cp "$UPDATE_SRC/backend/main.py" "$DIR/backend/main.py"

    # 覆盖前端文件
    cp "$UPDATE_SRC/frontend/equipment/index.html" "$DIR/frontend/equipment/"
    cp "$UPDATE_SRC/frontend/hazard/index.html" "$DIR/frontend/hazard/"
    cp "$UPDATE_SRC/frontend/incident/index.html" "$DIR/frontend/incident/"
    cp "$UPDATE_SRC/frontend/index.html" "$DIR/frontend/" 2>/dev/null || true

    # 查找并杀掉所有旧进程
    for OLD_PID in $(ps aux | grep "uvicorn.*main:app.*--port $PORT" | grep -v grep | awk '{print $2}'); do
        echo "    停止旧进程 PID=$OLD_PID"
        kill "$OLD_PID" 2>/dev/null || true
    done
    sleep 2

    # 启动新进程
    echo "    启动服务 (端口 $PORT, Shield 端口 $SHIELD_PORT)"
    cd "$DIR/backend"
    nohup env SHIELD_PORT="$SHIELD_PORT" python3 -m uvicorn main:app --host 0.0.0.0 --port "$PORT" > /tmp/ehs-${DIR}.log 2>&1 &
    cd - > /dev/null

    echo "    ✓ $DIR 更新完成"
done

# 清理临时目录
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
