"""安全联锁屏蔽 — 核心路由（页面入口）"""
from fastapi import APIRouter

core_router = APIRouter()


@core_router.get("/health")
def health():
    return {"status": "ok"}
