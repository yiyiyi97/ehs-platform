#!/bin/bash
# 排查复盘报告上传路径问题

echo "=== 1. 检查 drop-in 文件 ==="
for svc in ehs-dashboard ehs-wuhan ehs-beijing ehs-shanghai; do
    echo "--- $svc ---"
    cat /etc/systemd/system/${svc}.service.d/override.conf 2>/dev/null || echo "(文件不存在)"
done

echo ""
echo "=== 2. 检查 running 进程的实际环境变量 ==="
for pid in $(pgrep -f "uvicorn main:app"); do
    echo "--- PID $pid ---"
    cat /proc/$pid/environ 2>/dev/null | tr '\0' '\n' | grep -E "EHS_REPORT_BASE|EHS_REGION|PWD" || echo "(无环境变量)"
done

echo ""
echo "=== 3. 检查 service 文件内容 ==="
for svc in ehs-dashboard ehs-wuhan ehs-beijing ehs-shanghai; do
    echo "--- $svc ---"
    systemctl cat $svc 2>/dev/null | grep -E "ExecStart|Environment" || echo "(无相关配置)"
done

echo ""
echo "=== 4. 检查 uploads/incident 目录（默认路径） ==="
for dir in \
    /root/EHS_Dashboard/uploads/incident \
    /root/EHS_Dashboard_wuhan/uploads/incident \
    /root/EHS_Dashboard_beijing/uploads/incident \
    /root/EHS_Dashboard_shanghai/uploads/incident; do
    echo "--- $dir ---"
    ls -la "$dir" 2>/dev/null | head -5 || echo "(目录不存在或为空)"
done

echo ""
echo "=== 5. 测试创建目标目录 ==="
for region in 深圳 武汉 北京 上海; do
    target="/root/EHS_docs/documents/异常事件复盘/$region"
    touch "$region-test.tmp" && rm "$region-test.tmp"
    if [ $? -eq 0 ]; then
        echo "$region: 可写入 ✓"
    else
        echo "$region: 不可写入 ✗"
    fi
done
