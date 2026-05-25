"""Device CRUD API"""
from fastapi import APIRouter, HTTPException
from ehs_loto.models import SessionLocal, Device
from pydantic import BaseModel
from typing import Optional
import json

router = APIRouter()

class DeviceCreate(BaseModel):
    id: str
    name: str
    code: str
    type: str
    floor: int
    x: float = 0
    y: float = 0
    sub_system: str = ""
    energy_types: list = []
    loto_steps: list = []
    location: str = ""
    person: str = ""
    breakers: list = []

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    type: Optional[str] = None
    floor: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    sub_system: Optional[str] = None
    energy_types: Optional[list] = None
    loto_steps: Optional[list] = None
    location: Optional[str] = None
    is_locked: Optional[bool] = None
    locked_breaker_ids: Optional[list] = None
    is_affected: Optional[bool] = None
    affected_by_list: Optional[list] = None
    person: Optional[str] = None
    breakers: Optional[list] = None

@router.get("")
def list_devices():
    db = SessionLocal()
    try:
        return [d.to_dict() for d in db.query(Device).all()]
    finally:
        db.close()

@router.get("/floor/{floor}")
def list_by_floor(floor: int):
    db = SessionLocal()
    try:
        return [d.to_dict() for d in db.query(Device).filter(Device.floor == floor).all()]
    finally:
        db.close()

@router.get("/{device_id}")
def get_device(device_id: str):
    db = SessionLocal()
    try:
        d = db.query(Device).get(device_id)
        if not d:
            raise HTTPException(404, "Device not found")
        return d.to_dict()
    finally:
        db.close()

@router.post("")
def create_device(device: DeviceCreate):
    db = SessionLocal()
    try:
        d = Device(**device.model_dump())
        db.add(d)
        db.commit()
        return d.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    finally:
        db.close()

@router.put("/{device_id}")
def update_device(device_id: str, update: DeviceUpdate):
    db = SessionLocal()
    try:
        d = db.query(Device).get(device_id)
        if not d:
            raise HTTPException(404, "Device not found")
        for k, v in update.model_dump(exclude_unset=True).items():
            setattr(d, k, v)
        db.commit()
        return d.to_dict()
    finally:
        db.close()

@router.delete("/{device_id}")
def delete_device(device_id: str):
    db = SessionLocal()
    try:
        d = db.query(Device).get(device_id)
        if not d:
            raise HTTPException(404)
        # Also delete connections involving this device
        from ehs_loto.models import Connection
        db.query(Connection).filter((Connection.from_device_id == device_id) | (Connection.to_device_id == device_id)).delete()
        db.delete(d)
        db.commit()
        return {"ok": True}
    finally:
        db.close()

@router.post("/{device_id}/lock")
def lock_device(device_id: str, breaker_ids: list[str] = []):
    db = SessionLocal()
    try:
        d = db.query(Device).get(device_id)
        if not d:
            raise HTTPException(404)
        d.is_locked = True
        d.locked_breaker_ids = breaker_ids
        db.commit()
        return d.to_dict()
    finally:
        db.close()

@router.post("/{device_id}/unlock")
def unlock_device(device_id: str):
    db = SessionLocal()
    try:
        d = db.query(Device).get(device_id)
        if not d:
            raise HTTPException(404)
        d.is_locked = False
        d.locked_breaker_ids = []
        db.commit()
        return d.to_dict()
    finally:
        db.close()
