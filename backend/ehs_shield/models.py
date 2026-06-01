"""安全联锁屏蔽 — 数据库模型（复用旧 Shield SQLite 数据库）"""
from sqlalchemy import Column, String, Integer, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

Base = declarative_base()
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shield_backend", "data.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class ShieldItem(Base):
    __tablename__ = "shield_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    code = Column(String, default="")
    location = Column(String, default="")
    category = Column(String, default="")
    subsystem = Column(String, default="")
    version = Column(String, default="")
    created_at = Column(String, default="")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    applicant = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    meeting_minutes_path = Column(String)
    shield_screenshot_path = Column(String)
    expected_restore_time = Column(String, nullable=False)
    status = Column(String, default="active")
    created_at = Column(String, default="")
    restored_at = Column(String)
    restored_by = Column(String)
    version = Column(String)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ApplicationItem(Base):
    __tablename__ = "application_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, nullable=False)
    shield_item_id = Column(Integer, nullable=False)
    status = Column(String, default="active")
    restored_at = Column(String)
    restored_by = Column(String)
    created_at = Column(String, default="")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Version(Base):
    __tablename__ = "versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(String, default="")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
