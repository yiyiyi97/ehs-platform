"""审计日志 API"""
from fastapi import APIRouter, Depends
from ehs_equipment.models import SessionLocal, AuditLog, log_audit
from ehs_equipment.api.auth import get_current_user, require_admin
from datetime import datetime, timezone

router = APIRouter()


@router.get("")
def list_audit_logs(
    page: int = 1, size: int = 50,
    action: str = "", target_type: str = "", username: str = "",
    start_date: str = "", end_date: str = "",
    user=Depends(require_admin)
):
    db = SessionLocal()
    try:
        q = db.query(AuditLog)
        if action:
            q = q.filter(AuditLog.action == action)
        if target_type:
            q = q.filter(AuditLog.target_type == target_type)
        if username:
            q = q.filter(AuditLog.username.contains(username))
        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                q = q.filter(AuditLog.created_at >= start)
            except Exception:
                pass
        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc, hour=23, minute=59, second=59)
                q = q.filter(AuditLog.created_at <= end)
            except Exception:
                pass

        total = q.count()
        logs = q.order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size).all()
        return {"total": total, "page": page, "size": size, "items": [l.to_dict() for l in logs]}
    finally:
        db.close()


@router.get("/actions")
def list_actions(user=Depends(require_admin)):
    """返回所有操作类型，供前端筛选"""
    db = SessionLocal()
    try:
        actions = db.query(AuditLog.action).distinct().all()
        return {"actions": [a[0] for a in actions if a[0]]}
    finally:
        db.close()
