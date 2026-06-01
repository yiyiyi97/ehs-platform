"""安全联锁屏蔽 — 统计学"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ehs_shield.models import get_db

router = APIRouter()


@router.get("/stats")
def get_stats(version: str = Query(None), db: Session = Depends(get_db)):
    version_clause = "AND a.version = :version" if version else ""
    sql = text(f"""
        SELECT
            COUNT(*) as total_apps,
            COALESCE(SUM(
                (SELECT COUNT(*) FROM application_items WHERE application_id = a.id AND status = 'active')
            ), 0) as total_active,
            COALESCE(SUM(
                CASE WHEN a.expected_restore_time < datetime('now', 'localtime') THEN
                    (SELECT COUNT(*) FROM application_items WHERE application_id = a.id AND status = 'active')
                ELSE 0 END
            ), 0) as total_overdue
        FROM applications a
        WHERE a.status = 'active' {version_clause}
    """)
    row = db.execute(sql, {"version": version} if version else {}).fetchone()
    return {
        "totalApps": row.total_apps,
        "totalActive": row.total_active,
        "totalOverdue": row.total_overdue,
    }
