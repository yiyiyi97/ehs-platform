"""特种设备&计量设备管理平台 - 数据库模型"""
from sqlalchemy import Column, String, Integer, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone, timedelta
import os
import json

Base = declarative_base()
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "equipment.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


# ── 审计日志 ──
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=0)
    username = Column(String, default="")
    display_name = Column(String, default="")
    action = Column(String, nullable=False)          # create / update / delete / login / logout / upload
    target_type = Column(String, default="")         # equipment / auth / excel
    target_id = Column(String, default="")           # 记录ID
    target_name = Column(String, default="")         # 设备编号或名称
    before = Column(Text, default="")                # 修改前 JSON
    after = Column(Text, default="")                 # 修改后 JSON
    detail = Column(Text, default="")                # 额外描述
    ip = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "before": self.before,
            "after": self.after,
            "detail": self.detail,
            "ip": self.ip,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }



class FieldOption(Base):
    __tablename__ = "field_options"
    id = Column(Integer, primary_key=True, autoincrement=True)
    field_name = Column(String, nullable=False, index=True)
    value = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {"id": self.id, "field_name": self.field_name, "value": self.value, "sort_order": self.sort_order}


# ── 用户 ──
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    display_name = Column(String, default="")
    token = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "display_name": self.display_name or self.username
        }


# ── 设备台账 ──
class EquipmentRecord(Base):
    __tablename__ = "equipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_no = Column(String, nullable=False, index=True)       # 设备编号
    equipment_name = Column(String, nullable=False)                  # 设备名称
    equipment_type = Column(String, default="特种设备")               # 设备类型：特种设备/计量设备
    category = Column(String, default="")                           # 类别：压力容器/电梯/起重机械/叉车/安全阀/压力表/温度计等
    lab = Column(String, default="")                                # 实验室/区域
    floor = Column(String, default="")                              # 楼层
    manufacturer = Column(String, default="")                       # 制造商
    model = Column(String, default="")                              # 型号规格
    serial_no = Column(String, default="")                          # 出厂编号/序列号
    location = Column(String, default="")                           # 安装位置
    responsible_person = Column(String, default="")                 # 责任人
    responsible_dept = Column(String, default="")                   # 责任部门
    purchase_date = Column(String, default="")                      # 采购日期
    commissioning_date = Column(String, default="")                 # 投用日期
    last_check_date = Column(String, default="")                    # 上次校验日期
    next_check_date = Column(String, default="")                    # 下次校验日期
    check_cycle = Column(Integer, default=12)                        # 校验周期（月）
    cert_no = Column(String, default="")                            # 证书编号
    cert_photo = Column(String, default="")                         # 证照图片URL
    status = Column(String, default="在用")                          # 设备状态：在用/停用/报废
    remark = Column(Text, default="")                               # 备注
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        result = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name)
            if isinstance(v, datetime):
                v = v.isoformat()
            result[c.name] = v
        # 计算校验状态
        result["check_status"] = self._compute_check_status()
        result["days_to_check"] = self._compute_days_to_check()
        return result

    def _compute_check_status(self):
        """计算校验状态：正常/临期/超期"""
        if not self.next_check_date:
            return "未知"
        try:
            next_date = datetime.strptime(self.next_check_date, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            if today > next_date:
                return "超期"
            elif (next_date - today).days <= 30:
                return "临期"
            else:
                return "正常"
        except Exception:
            return "未知"

    def _compute_days_to_check(self):
        """计算距离下次校验还剩多少天"""
        if not self.next_check_date:
            return None
        try:
            next_date = datetime.strptime(self.next_check_date, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            return (next_date - today).days
        except Exception:
            return None


# ── 审计日志辅助函数 ──
def log_audit(user, action: str, target_type: str, target_id: str = "", target_name: str = "",
              before: dict = None, after: dict = None, detail: str = "", ip: str = ""):
    """记录审计日志（同步写入，失败不阻断主流程）"""
    try:
        db = SessionLocal()
        try:
            log = AuditLog(
                user_id=getattr(user, "id", 0) or 0,
                username=getattr(user, "username", "") or "",
                display_name=getattr(user, "display_name", "") or getattr(user, "username", "") or "",
                action=action,
                target_type=target_type,
                target_id=str(target_id) if target_id else "",
                target_name=target_name or "",
                before=json.dumps(before, ensure_ascii=False, default=str) if before else "",
                after=json.dumps(after, ensure_ascii=False, default=str) if after else "",
                detail=detail,
                ip=ip,
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass  # 审计日志失败不影响主业务


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed default admin user
        if db.query(User).filter(User.username == "protector").first() is None:
            import bcrypt
            hashed = bcrypt.hashpw("protector".encode(), bcrypt.gensalt()).decode()
            db.add(User(username="protector", password_hash=hashed, role="admin", display_name="管理员"))
            db.commit()

        # Seed default options
        if db.query(FieldOption).count() == 0:
            defaults = [
                ("equipment_type", "特种设备"), ("equipment_type", "计量设备"),
                ("category", "压力容器"), ("category", "电梯"), ("category", "起重机械"),
                ("category", "叉车"), ("category", "安全阀"), ("category", "压力表"),
                ("category", "温度计"), ("category", "流量计"), ("category", "可燃气体探测器"),
                ("category", "其他"),
                ("lab", "L1"), ("lab", "L2"), ("lab", "L3"),
                ("floor", "1F"), ("floor", "2F"), ("floor", "3F"),
                ("status", "在用"), ("status", "停用"), ("status", "报废"),
                ("check_cycle", "3"), ("check_cycle", "6"), ("check_cycle", "12"),
                ("check_cycle", "24"), ("check_cycle", "36"),
            ]
            for fn, val in defaults:
                db.add(FieldOption(field_name=fn, value=val))
            db.commit()
    finally:
        db.close()
