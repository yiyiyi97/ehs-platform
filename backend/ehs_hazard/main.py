"""隐患/风险数据管理平台 — adapted for unified EHS Dashboard"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from ehs_hazard.models import init_db
from ehs_hazard.api import hazards, options, excel, stats, auth
import traceback

# ── Core router (mounted at /api/hazard in unified app) ──
core_router = APIRouter()

@core_router.get("/health")
def health():
    return {"status": "ok"}

async def global_exception_handler(request: Request, exc: Exception):
    print(f"ERROR: {exc}\n{traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"error": str(exc)})
