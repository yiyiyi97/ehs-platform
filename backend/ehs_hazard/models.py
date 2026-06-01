"""隐患/风险数据管理平台 - 数据库模型"""
from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import os

Base = declarative_base()
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hazard.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


# ── 字段下拉选项（可自定义）──
class FieldOption(Base):
    __tablename__ = "field_options"
    id = Column(Integer, primary_key=True, autoincrement=True)
    field_name = Column(String, nullable=False, index=True)  # e.g. "risk_level", "lab"
    value = Column(String, nullable=False)                   # display text
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
    role = Column(String, default="user")          # admin | user
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


# ── 隐患记录 ──
class HazardRecord(Base):
    __tablename__ = "hazards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hazard_no = Column(String, nullable=False, index=True)        # 隐患单号
    lab = Column(String, default="")                              # 实验室
    floor = Column(String, default="")                            # 楼层
    subsystem = Column(String, default="")                        # 子系统
    risk_level = Column(String, default="Medium")                 # 风险等级
    risk_type = Column(String, default="")                        # 风险类型
    check_type = Column(String, default="")                       # 检查类型
    equipment = Column(String, default="")                        # 相关设备
    equipment_phase = Column(String, default="")                  # 设备阶段
    risk_desc = Column(Text, default="")                          # 风险描述
    status = Column(String, default="open")                       # 状态
    reporter = Column(String, default="")                         # 提出人
    report_date = Column(String, default="")                      # 提出日期
    responsible_person = Column(String, default="")               # 整改责任人
    responsible_id = Column(String, default="")                   # 责任人工号
    responsible_dept = Column(String, default="")                 # 责任人部门
    expected_close_date = Column(String, default="")              # 期望闭环日期
    close_date = Column(String, default="")                       # 闭环时间
    verifier = Column(String, default="")                         # 验收人员
    fix_suggestion = Column(Text, default="")                     # 整改建议
    fix_progress = Column(Text, default="")                       # 整改进展
    photo_before = Column(String, default="")                     # 整改前照片(URL)
    photo_after = Column(String, default="")                      # 整改后照片(URL)
    interface_person = Column(String, default="")                 # 集成接口人
    need_issue = Column(String, default="")                       # 是否需要提问题单
    issue_no = Column(String, default="")                         # 具体问题单号
    need_sde = Column(String, default="")                         # 是否须在SDE闭环
    overdue_impact = Column(Text, default="")                     # 整改逾期对项目的影响
    version = Column(String, default="")                              # 版本
    extra = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        result = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name)
            if isinstance(v, datetime):
                v = v.isoformat()
            result[c.name] = v
        return result


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
                ("lab", "L1"), ("lab", "L2"), ("lab", "L3"),
                ("floor", "1F"), ("floor", "2F"), ("floor", "3F"),
                ("risk_level", "Low"), ("risk_level", "Medium"), ("risk_level", "High"),
                ("risk_type", "电气"), ("risk_type", "水"), ("risk_type", "气体"),
                ("risk_type", "机械"), ("risk_type", "激光"), ("risk_type", "其他"),
                ("check_type", "日常巡检"), ("check_type", "专项检查"), ("check_type", "事故排查"),
                ("check_type", "内审"), ("check_type", "外审"),
                ("equipment_phase", "安装"), ("equipment_phase", "调试"), ("equipment_phase", "验收"),
                ("equipment_phase", "运行"), ("equipment_phase", "维护"), ("equipment_phase", "退役"),
                ("status", "open"), ("status", "挂起"), ("status", "closed"),
                ("need_issue", "是"), ("need_issue", "否"),
                ("need_sde", "是"), ("need_sde", "否"),
            ]
            for fn, val in defaults:
                db.add(FieldOption(field_name=fn, value=val))
            db.commit()
    finally:
        db.close()
