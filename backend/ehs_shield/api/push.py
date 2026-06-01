"""安全联锁屏蔽 — WeLink 推送"""
import urllib.request
import urllib.error
import json
import uuid
import time
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ehs_shield.models import get_db

router = APIRouter()

WELINK_WEBHOOK_URL = os.getenv("WELINK_WEBHOOK_URL", "")


def _send_welink_message(content: str, is_at_all: bool = False, at_accounts: Optional[list] = None) -> Optional[Dict[str, Any]]:
    if not WELINK_WEBHOOK_URL:
        return None
    if len(content) > 500:
        content = content[:497] + "..."
    body = {
        "messageType": "text",
        "content": {"text": content},
        "timeStamp": int(time.time() * 1000),
        "uuid": str(uuid.uuid4()).replace("-", ""),
        "isAt": bool(at_accounts) or is_at_all,
        "isAtAll": is_at_all,
    }
    if at_accounts and not is_at_all:
        body["atAccounts"] = at_accounts[:10]
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(WELINK_WEBHOOK_URL, data=data, headers={"Content-Type": "application/json; charset=UTF-8"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"message": str(e), "code": "-1"}


@router.post("/push/welink-test")
async def welink_test():
    if not WELINK_WEBHOOK_URL:
        raise HTTPException(status_code=503, detail="WeLink webhook 未配置")
    msg = f"【EHS测试】安全联锁系统测试消息\n时间：{time.strftime('%Y-%m-%d %H:%M:%S')}"
    result = _send_welink_message(msg)
    if result and result.get("code") == "0":
        return {"success": True, "message": "测试消息已发送"}
    raise HTTPException(status_code=502, detail=result.get("message", "发送失败") if result else "发送失败")


@router.post("/push/welink-daily")
async def welink_daily(data: dict, db: Session = Depends(get_db)):
    if not WELINK_WEBHOOK_URL:
        raise HTTPException(status_code=503, detail="WeLink webhook 未配置")
    is_at_all = data.get("is_at_all", False)
    at_accounts = data.get("at_accounts", [])

    row = db.execute(text("""
        SELECT COUNT(*) as total_apps,
            COALESCE(SUM((SELECT COUNT(*) FROM application_items WHERE application_id = a.id AND status = 'active')), 0) as total_active,
            COALESCE(SUM(CASE WHEN a.expected_restore_time < datetime('now','localtime') THEN (SELECT COUNT(*) FROM application_items WHERE application_id = a.id AND status = 'active') ELSE 0 END), 0) as total_overdue
        FROM applications a WHERE a.status = 'active'
    """)).fetchone()
    rd = dict(row._mapping)

    overdue_items = db.execute(text("""
        SELECT si.name as device_code, ROUND((julianday('now') - julianday(a.expected_restore_time)) * 24, 1) as overdue_hours
        FROM application_items ai
        JOIN shield_items si ON ai.shield_item_id = si.id
        JOIN applications a ON ai.application_id = a.id
        WHERE ai.status = 'active' AND a.expected_restore_time < datetime('now','localtime')
        ORDER BY a.expected_restore_time ASC LIMIT 8
    """)).fetchall()

    lines = [f"【EHS安全联锁日报】{time.strftime('%Y-%m-%d')}", ""]
    lines.append(f"活跃屏蔽项：{rd['total_active']} 个")
    lines.append(f"超时未恢复：{rd['total_overdue']} 个")

    if overdue_items:
        lines.append("")
        lines.append("超时明细：")
        for item in overdue_items:
            d = dict(item._mapping)
            h = d["overdue_hours"]
            dur = f"{int(h//24)}天{int(h%24)}小时" if h >= 24 else f"{int(h)}小时"
            lines.append(f"  · {d['device_code']} （超时{dur}）")

    report = "\n".join(lines)
    result = _send_welink_message(report, is_at_all=is_at_all, at_accounts=at_accounts)
    if result and result.get("code") == "0":
        return {"success": True, "message": "日报已推送到 WeLink 群"}
    raise HTTPException(status_code=502, detail=result.get("message", "发送失败") if result else "发送失败")
