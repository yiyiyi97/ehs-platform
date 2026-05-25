"""字段选项管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from ehs_incident.models import SessionLocal, Option
from ehs_incident.api.auth import require_admin

router = APIRouter()


@router.get("/fields")
def list_fields(user=Depends(require_admin)):
    db = SessionLocal()
    try:
        rows = db.query(Option).all()
        result = {}
        for r in rows:
            result.setdefault(r.field_name, []).append(r.value)
        return result
    finally:
        db.close()


@router.get("")
def list_options(field: str = "", user=Depends(require_admin)):
    db = SessionLocal()
    try:
        q = db.query(Option)
        if field:
            q = q.filter(Option.field_name == field)
        return [{"id": o.id, "field_name": o.field_name, "value": o.value} for o in q.all()]
    finally:
        db.close()


@router.post("")
def add_option(data: dict, user=Depends(require_admin)):
    db = SessionLocal()
    try:
        field_name = data.get("field_name", "").strip()
        value = data.get("value", "").strip()
        if not field_name or not value:
            raise HTTPException(400, "字段名和值不能为空")
        exists = db.query(Option).filter(Option.field_name == field_name, Option.value == value).first()
        if exists:
            raise HTTPException(400, "该选项已存在")
        o = Option(field_name=field_name, value=value)
        db.add(o)
        db.commit()
        db.refresh(o)
        return {"id": o.id, "field_name": o.field_name, "value": o.value}
    finally:
        db.close()


@router.delete("/{option_id}")
def delete_option(option_id: int, user=Depends(require_admin)):
    db = SessionLocal()
    try:
        o = db.query(Option).get(option_id)
        if not o:
            raise HTTPException(404)
        db.delete(o)
        db.commit()
        return {"ok": True}
    finally:
        db.close()
