"""特种设备&计量设备管理 — 核心路由"""
from fastapi import APIRouter
from ehs_equipment.models import init_db

core_router = APIRouter()


@core_router.get("/health")
def health():
    return {"status": "ok"}
