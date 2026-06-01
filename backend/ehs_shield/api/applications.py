"""安全联锁屏蔽 — 申请管理"""
import json
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from ehs_shield.models import Application, ApplicationItem, get_db
from typing import Optional

router = APIRouter()
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "uploads")


@router.get("/applications")
def list_applications(version: Optional[str] = Query(None), db: Session = Depends(get_db)):
    ver_clause = "AND a.version = :ver" if version else ""
    sql = text(f"""
        SELECT a.*,
            (SELECT COUNT(*) FROM application_items WHERE application_id = a.id) as total_items,
            (SELECT COUNT(*) FROM application_items WHERE application_id = a.id AND status = 'active') as active_items,
            (SELECT GROUP_CONCAT(si.name, '、') FROM application_items ai JOIN shield_items si ON ai.shield_item_id = si.id WHERE ai.application_id = a.id) as item_names
        FROM applications a
        WHERE 1=1 {ver_clause}
        ORDER BY a.created_at DESC
    """)
    params = {"ver": version} if version else {}
    rows = db.execute(sql, params).fetchall()
    result = []
    for row in rows:
        d = dict(row._mapping)
        d.setdefault("total_items", 0)
        d.setdefault("active_items", 0)
        d.setdefault("item_names", "")
        result.append(d)
    return result


@router.get("/applications/{app_id}")
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).get(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="申请不存在")
    return app.to_dict()


@router.get("/applications/{app_id}/items")
def get_application_items(app_id: int, db: Session = Depends(get_db)):
    sql = text("""
        SELECT ai.*, si.name as shield_item_name,
               si.category as shield_item_category,
               si.subsystem as shield_item_subsystem
        FROM application_items ai
        JOIN shield_items si ON ai.shield_item_id = si.id
        WHERE ai.application_id = :app_id
        ORDER BY si.id
    """)
    rows = db.execute(sql, {"app_id": app_id}).fetchall()
    return [dict(r._mapping) for r in rows]


@router.post("/applications")
async def create_application(
    applicant: str = Form(""),
    reason: str = Form(""),
    expected_restore_time: str = Form(""),
    shield_item_ids: str = Form(""),
    version: str = Form(""),
    meeting_minutes: Optional[UploadFile] = File(None),
    shield_screenshot: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    if not applicant or not reason or not expected_restore_time or not shield_item_ids:
        raise HTTPException(status_code=400, detail="缺少必填字段")

    try:
        item_ids = json.loads(shield_item_ids)
        if not isinstance(item_ids, list) or len(item_ids) == 0:
            raise ValueError()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="shield_item_ids 必须是有效的数字数组")

    os.makedirs(UPLOADS_DIR, exist_ok=True)

    meeting_path = None
    screenshot_path = None
    if meeting_minutes and meeting_minutes.filename:
        meeting_path = f"{int(datetime.utcnow().timestamp() * 1000)}-{meeting_minutes.filename}"
        with open(os.path.join(UPLOADS_DIR, meeting_path), "wb") as f:
            f.write(await meeting_minutes.read())
    if shield_screenshot and shield_screenshot.filename:
        screenshot_path = f"{int(datetime.utcnow().timestamp() * 1000)}-{shield_screenshot.filename}"
        with open(os.path.join(UPLOADS_DIR, screenshot_path), "wb") as f:
            f.write(await shield_screenshot.read())

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app = Application(
        applicant=applicant,
        reason=reason,
        meeting_minutes_path=meeting_path,
        shield_screenshot_path=screenshot_path,
        expected_restore_time=expected_restore_time,
        status="active",
        created_at=now_str,
        version=version,
    )
    db.add(app)
    db.flush()

    for item_id in item_ids:
        db.add(ApplicationItem(application_id=app.id, shield_item_id=item_id, status="active", created_at=now_str))

    db.commit()
    db.refresh(app)
    return {"id": app.id}


@router.post("/applications/{app_id}/complete")
def complete_application(app_id: int, data: dict, db: Session = Depends(get_db)):
    restored_by = data.get("restored_by", "系统")
    item_ids = data.get("item_ids")
    dry_run = data.get("dry_run", False)

    # Get active items
    sql = text("""
        SELECT ai.id, ai.shield_item_id, si.name as shield_item_name
        FROM application_items ai
        JOIN shield_items si ON ai.shield_item_id = si.id
        WHERE ai.application_id = :app_id AND ai.status = 'active'
    """)
    active_items = [dict(r._mapping) for r in db.execute(sql, {"app_id": app_id}).fetchall()]

    if not active_items:
        return {"can_complete": True, "conflicts": [], "items": []}

    # Check conflicts
    conflicts = []
    for item in active_items:
        conflict_sql = text("""
            SELECT a.id, a.applicant, a.reason
            FROM application_items ai
            JOIN applications a ON ai.application_id = a.id
            WHERE ai.shield_item_id = :item_id AND ai.application_id != :app_id AND ai.status = 'active'
        """)
        conflict_rows = db.execute(conflict_sql, {"item_id": item["shield_item_id"], "app_id": app_id}).fetchall()
        for c in conflict_rows:
            cd = dict(c._mapping)
            conflicts.append({
                "item_id": item["id"],
                "shield_item_id": item["shield_item_id"],
                "shield_item_name": item["shield_item_name"],
                "conflict_application_id": cd["id"],
                "applicant": cd["applicant"],
                "reason": cd["reason"],
            })

    if dry_run:
        return {"can_complete": len(conflicts) == 0, "conflicts": conflicts, "items": active_items}

    target_ids = item_ids if isinstance(item_ids, list) and len(item_ids) > 0 else [i["id"] for i in active_items]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    app = db.query(Application).get(app_id)
    if app:
        app.status = "restored"
        app.restored_at = now_str
        app.restored_by = restored_by

    for target_id in target_ids:
        item = db.query(ApplicationItem).get(target_id)
        if item and item.status == "active":
            item.status = "restored"
            item.restored_at = now_str
            item.restored_by = restored_by

    db.commit()
    return {"success": True, "restored": len(target_ids)}


@router.put("/applications/{app_id}/extend")
def extend_application(app_id: int, data: dict, db: Session = Depends(get_db)):
    new_time = data.get("expected_restore_time", "").strip()
    if not new_time:
        raise HTTPException(status_code=400, detail="请提供新的预期恢复时间")
    app = db.query(Application).get(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="申请不存在")
    app.expected_restore_time = new_time
    db.commit()
    return {"ok": True}


@router.delete("/applications/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).get(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="申请不存在")
    db.execute(text("DELETE FROM application_items WHERE application_id = :id"), {"id": app_id})
    db.delete(app)
    db.commit()
    return {"ok": True}


@router.get("/ledger")
def get_ledger(version: Optional[str] = Query(None), db: Session = Depends(get_db)):
    ver_clause = "AND a.version = :ver" if version else ""
    sql = text(f"""
        SELECT ai.id, ai.application_id, ai.shield_item_id, ai.status,
               ai.restored_at, ai.restored_by, ai.created_at,
               si.name as shield_item_name,
               si.category as shield_item_category,
               si.subsystem as shield_item_subsystem,
               a.applicant, a.reason,
               a.meeting_minutes_path, a.shield_screenshot_path,
               a.expected_restore_time, a.status as application_status,
               a.created_at as application_created_at,
               a.version
        FROM application_items ai
        JOIN shield_items si ON ai.shield_item_id = si.id
        JOIN applications a ON ai.application_id = a.id
        WHERE ai.status = 'active' {ver_clause}
        ORDER BY
            CASE WHEN a.expected_restore_time < datetime('now', 'localtime') THEN 0 ELSE 1 END,
            a.expected_restore_time ASC
    """)
    params = {"ver": version} if version else {}
    rows = db.execute(sql, params).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/history")
def get_history(version: Optional[str] = Query(None), db: Session = Depends(get_db)):
    ver_clause = "AND a.version = :ver" if version else ""
    sql = text(f"""
        SELECT ai.id, ai.application_id, ai.shield_item_id, ai.status,
               ai.restored_at, ai.restored_by, ai.created_at,
               si.name as shield_item_name,
               si.category as shield_item_category,
               si.subsystem as shield_item_subsystem,
               a.applicant, a.reason,
               a.meeting_minutes_path, a.shield_screenshot_path,
               a.expected_restore_time, a.created_at as application_created_at,
               a.version,
               (SELECT COUNT(*) FROM application_items WHERE shield_item_id = ai.shield_item_id) as shield_count
        FROM application_items ai
        JOIN shield_items si ON ai.shield_item_id = si.id
        JOIN applications a ON ai.application_id = a.id
        WHERE ai.status = 'restored' {ver_clause}
        ORDER BY ai.restored_at DESC
    """)
    params = {"ver": version} if version else {}
    rows = db.execute(sql, params).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/versions")
def list_versions(db: Session = Depends(get_db)):
    from ehs_shield.models import Version
    return db.query(Version).order_by(Version.id).all()


@router.post("/versions")
def create_version(data: dict, db: Session = Depends(get_db)):
    from ehs_shield.models import Version
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="版本名称不能为空")
    existing = db.query(Version).filter(Version.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="版本名称已存在")
    v = Version(name=name, created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    db.add(v)
    db.commit()
    db.refresh(v)
    return v.to_dict()
