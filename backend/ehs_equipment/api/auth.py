"""用户认证 API — 复用 hazard 的认证（统一账户）"""
from ehs_hazard.api.auth import (
    get_current_user, require_admin, get_current_user_optional,
    hash_password, verify_password
)
from ehs_hazard.models import SessionLocal, User
from fastapi import APIRouter, HTTPException, Depends
import uuid

router = APIRouter()


@router.post("/login")
def login(data: dict):
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        user.token = str(uuid.uuid4())
        db.commit()
        return {"token": user.token, "user": user.to_dict()}
    finally:
        db.close()


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        user.token = ""
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user.to_dict()


@router.post("/register")
def register(data: dict, admin: User = Depends(require_admin)):
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "user")
    display_name = data.get("display_name", "").strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="角色必须是 admin 或 user")

    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(status_code=400, detail="用户名已存在")

        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            display_name=display_name or username
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.to_dict()
    finally:
        db.close()


@router.get("/users")
def list_users(admin: User = Depends(require_admin)):
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return [u.to_dict() for u in users]
    finally:
        db.close()


@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_admin)):
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    db = SessionLocal()
    try:
        user = db.query(User).get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        db.delete(user)
        db.commit()
        return {"ok": True}
    finally:
        db.close()
