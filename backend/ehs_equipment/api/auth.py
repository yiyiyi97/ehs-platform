"""用户认证 API"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ehs_equipment.models import SessionLocal, User, log_audit
import bcrypt
import uuid

router = APIRouter()
security = HTTPBearer(auto_error=False)


def hash_password(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


def verify_password(pwd: str, hashed: str) -> bool:
    return bcrypt.checkpw(pwd.encode(), hashed.encode())


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录")
    token = credentials.credentials
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.token == token).first()
        if not user:
            raise HTTPException(status_code=401, detail="登录已过期")
        return user
    finally:
        db.close()


def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    token = credentials.credentials
    db = SessionLocal()
    try:
        return db.query(User).filter(User.token == token).first()
    finally:
        db.close()


def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


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
            log_audit(None, "login", "auth", target_name=username, detail="登录失败：用户名或密码错误")
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        user.token = str(uuid.uuid4())
        db.commit()
        log_audit(user, "login", "auth", target_id=user.id, target_name=user.username, detail="登录成功")
        return {"token": user.token, "user": user.to_dict()}
    finally:
        db.close()


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        user.token = ""
        db.commit()
        log_audit(user, "logout", "auth", target_id=user.id, target_name=user.username, detail="登出成功")
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
        log_audit(admin, "create", "auth", target_id=user.id, target_name=username, detail=f"注册新用户: {username} ({role})")
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
        log_audit(admin, "delete", "auth", target_id=user_id, target_name=user.username, detail=f"删除用户: {user.username}")
        db.delete(user)
        db.commit()
        return {"ok": True}
    finally:
        db.close()
