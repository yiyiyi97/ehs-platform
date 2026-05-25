"""异常事件管理 API"""
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File
from fastapi.responses import FileResponse
from ehs_incident.models import SessionLocal, IncidentRecord
from ehs_incident.api.auth import get_current_user, require_admin
from sqlalchemy import func, case
import os
import uuid
from datetime import datetime

router = APIRouter()

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 复盘报告目录（优先从环境变量读取，否则使用项目下 uploads/incident）
REPORT_BASE = os.getenv("EHS_REPORT_BASE", os.path.join(BASE_DIR, "uploads", "incident"))
REGION = os.getenv("EHS_REGION", "")
REPORT_DIR = os.path.join(REPORT_BASE, REGION) if REGION else REPORT_BASE
os.makedirs(REPORT_DIR, exist_ok=True)

# 旧上传目录（兼容旧数据下载）
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads", "incident")
os.makedirs(UPLOADS_DIR, exist_ok=True)


@router.get("")
def list_incidents(
    page: int = 1, size: int = 50, status: str = "", search: str = "",
    incident_type: str = "", event_level: str = "", lab: str = "", version: str = "",
    subsystem: str = "", device_name: str = "",
    sort_by: str = "", sort_order: str = "desc",
    user=Depends(get_current_user)
):
    db = SessionLocal()
    try:
        q = db.query(IncidentRecord)
        if status: q = q.filter(IncidentRecord.status == status)
        if incident_type: q = q.filter(IncidentRecord.incident_type == incident_type)
        if event_level: q = q.filter(IncidentRecord.event_level == event_level)
        if lab: q = q.filter(IncidentRecord.lab == lab)
        if version: q = q.filter(IncidentRecord.version == version)
        if subsystem: q = q.filter(IncidentRecord.subsystem == subsystem)
        if device_name: q = q.filter(IncidentRecord.device_name == device_name)
        if search:
            kw = f"%{search}%"
            q = q.filter(
                (IncidentRecord.incident_no.like(kw)) |
                (IncidentRecord.description.like(kw)) |
                (IncidentRecord.device_name.like(kw)) |
                (IncidentRecord.reporter.like(kw))
            )
        total = q.count()

        order_dir = sort_order.lower() if sort_order.lower() in ("asc", "desc") else "desc"
        if sort_by == "report_date":
            col = IncidentRecord.report_date
            q = q.order_by(col.asc() if order_dir == "asc" else col.desc())
        elif sort_by == "review_date":
            col = IncidentRecord.review_date
            q = q.order_by(col.asc() if order_dir == "asc" else col.desc())
        else:
            q = q.order_by(IncidentRecord.id.desc())

        items = q.offset((page - 1) * size).limit(size).all()
        return {"total": total, "page": page, "size": size, "items": [h.to_dict() for h in items]}
    finally:
        db.close()


@router.get("/{incident_id}")
def get_incident(incident_id: int, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        h = db.query(IncidentRecord).get(incident_id)
        if not h:
            raise HTTPException(404)
        return h.to_dict()
    finally:
        db.close()


@router.post("")
def create_incident(data: dict, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        # 自动生成单号
        today = datetime.now().strftime("%Y%m%d")
        prefix = data.get("lab", "") or ""
        existing = db.query(IncidentRecord).filter(
            IncidentRecord.incident_no.like(f"{today}{prefix}%")
        ).count()
        data["incident_no"] = f"{today}{prefix}{existing + 1:02d}"

        h = IncidentRecord(**{k: v for k, v in data.items() if k in IncidentRecord.__table__.columns.keys()})
        db.add(h)
        db.commit()
        db.refresh(h)
        return h.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.put("/{incident_id}")
def update_incident(incident_id: int, data: dict, user=Depends(require_admin)):
    db = SessionLocal()
    try:
        h = db.query(IncidentRecord).get(incident_id)
        if not h:
            raise HTTPException(404)
        for k, v in data.items():
            if k in IncidentRecord.__table__.columns.keys() and k != "id":
                setattr(h, k, v)
        db.commit()
        return h.to_dict()
    finally:
        db.close()


@router.delete("/{incident_id}")
def delete_incident(incident_id: int, user=Depends(require_admin)):
    db = SessionLocal()
    try:
        h = db.query(IncidentRecord).get(incident_id)
        if not h:
            raise HTTPException(404)
        # 删除关联文件
        if h.review_report_path:
            for d in (REPORT_DIR, UPLOADS_DIR):
                fp = os.path.join(d, h.review_report_path)
                if os.path.exists(fp):
                    os.remove(fp)
        db.delete(h)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/{incident_id}/upload")
def upload_report(incident_id: int, file: UploadFile = File(...), user=Depends(require_admin)):
    """上传复盘报告"""
    db = SessionLocal()
    try:
        h = db.query(IncidentRecord).get(incident_id)
        if not h:
            raise HTTPException(404)

        # 使用原始文件名，重名自动加序号
        base, ext = os.path.splitext(file.filename)
        filename = file.filename
        n = 1
        while os.path.exists(os.path.join(REPORT_DIR, filename)):
            n += 1
            filename = f"{base} ({n}){ext}"
        filepath = os.path.join(REPORT_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(file.file.read())

        # 删除旧文件
        if h.review_report_path:
            old = os.path.join(REPORT_DIR, h.review_report_path)
            if not os.path.exists(old):
                old = os.path.join(UPLOADS_DIR, h.review_report_path)
            if os.path.exists(old):
                os.remove(old)

        h.review_report_path = filename
        h.status = "已复盘"
        h.review_date = datetime.now().strftime("%Y-%m-%d")
        h.reviewer = user.display_name or user.username or ""
        db.commit()
        return {"ok": True, "filename": filename}
    finally:
        db.close()


@router.get("/{incident_id}/download")
def download_report(incident_id: int, user=Depends(get_current_user)):
    """下载复盘报告"""
    db = SessionLocal()
    try:
        h = db.query(IncidentRecord).get(incident_id)
        if not h or not h.review_report_path:
            raise HTTPException(404, "报告不存在")
        filepath = os.path.join(REPORT_DIR, h.review_report_path)
        if not os.path.exists(filepath):
            filepath = os.path.join(UPLOADS_DIR, h.review_report_path)
        if not os.path.exists(filepath):
            raise HTTPException(404, "文件已删除")
        return FileResponse(filepath, filename=h.review_report_path)
    finally:
        db.close()
