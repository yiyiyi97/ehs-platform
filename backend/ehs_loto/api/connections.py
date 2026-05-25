"""Connection API"""
from fastapi import APIRouter, HTTPException
from ehs_loto.models import SessionLocal, Connection
from pydantic import BaseModel

router = APIRouter()

class ConnectionCreate(BaseModel):
    id: str
    from_device_id: str
    to_device_id: str
    from_floor: int
    to_floor: int
    label: str = ""

@router.get("")
def list_connections():
    db = SessionLocal()
    try:
        return [c.to_dict() for c in db.query(Connection).all()]
    finally:
        db.close()

@router.post("")
def create_connection(conn: ConnectionCreate):
    db = SessionLocal()
    try:
        # Map snake_case to model fields
        c = Connection(**conn.model_dump())
        db.add(c)
        db.commit()
        return c.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    finally:
        db.close()

@router.delete("/{conn_id}")
def delete_connection(conn_id: str):
    db = SessionLocal()
    try:
        c = db.query(Connection).get(conn_id)
        if not c:
            raise HTTPException(404)
        db.delete(c)
        db.commit()
        return {"ok": True}
    finally:
        db.close()
