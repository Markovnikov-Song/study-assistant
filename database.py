"""
数据库模块：SQLAlchemy 懒加载 engine、session 工厂，以及所有表的 ORM 模型定义。
engine 在首次调用 get_engine() 时才创建，模块导入时不建立连接。
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

# ---------------------------------------------------------------------------
# ORM 基类
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# 表模型定义
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    subjects = relationship("Subject", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    conversation_sessions = relationship(
        "ConversationSession", back_populates="user", cascade="all, delete-orphan"
    )
    past_exam_files = relationship(
        "PastExamFile", back_populates="user", cascade="all, delete-orphan"
    )


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    category = Column(String(64))
    description = Column(Text)
    is_pinned = Column(Integer, default=0, nullable=False)   # 1=置顶 0=普通
    is_archived = Column(Integer, default=0, nullable=False) # 1=归档 0=正常
    sort_order = Column(Integer, default=0, nullable=False)  # 手动排序
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", back_populates="subjects")
    documents = relationship("Document", back_populates="subject", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="subject", cascade="all, delete-orphan")
    conversation_sessions = relationship(
        "ConversationSession", back_populates="subject", cascade="all, delete-orphan"
    )
    past_exam_files = relationship(
        "PastExamFile", back_populates="subject", cascade="all, delete-orphan"
    )
    past_exam_questions = relationship(
        "PastExamQuestion", back_populates="subject", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(256), nullable=False)
    status = Column(String(16), default="pending", nullable=False)  # pending/processing/completed/failed
    error = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    subject = relationship("Subject", back_populates="documents")
    user = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    document = relationship("Document", back_populates="chunks")
    subject = relationship("Subject", back_populates="chunks")


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(256))
    session_type = Column(String(32), default="qa")  # qa/solve/mindmap/exam
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", back_populates="conversation_sessions")
    subject = relationship("Subject", back_populates="conversation_sessions")
    history = relationship(
        "ConversationHistory", back_populates="session", cascade="all, delete-orphan"
    )


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Integer, ForeignKey("conversation_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(16), nullable=False)  # user/assistant
    content = Column(Text, nullable=False)
    sources = Column(JSONB)  # 引用来源列表
    scope_choice = Column(String(16))  # strict/broad
    created_at = Column(DateTime, default=func.now(), nullable=False)

    session = relationship("ConversationSession", back_populates="history")


class PastExamFile(Base):
    __tablename__ = "past_exam_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(256), nullable=False)
    status = Column(String(16), default="pending", nullable=False)  # pending/processing/completed/failed
    error = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    subject = relationship("Subject", back_populates="past_exam_files")
    user = relationship("User", back_populates="past_exam_files")
    questions = relationship(
        "PastExamQuestion", back_populates="exam_file", cascade="all, delete-orphan"
    )


class PastExamQuestion(Base):
    __tablename__ = "past_exam_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_file_id = Column(
        Integer, ForeignKey("past_exam_files.id", ondelete="CASCADE"), nullable=False
    )
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    question_number = Column(String(16))
    content = Column(Text, nullable=False)
    answer = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    exam_file = relationship("PastExamFile", back_populates="questions")
    subject = relationship("Subject", back_populates="past_exam_questions")


# ---------------------------------------------------------------------------
# 懒加载 Engine 与 Session 工厂
# ---------------------------------------------------------------------------

_engine = None
_SessionFactory = None


def get_engine():
    """
    返回 SQLAlchemy engine（懒加载：首次调用时才创建）。
    使用 pool_pre_ping=True 保证连接健康，pool_size=5，max_overflow=10。
    """
    global _engine
    if _engine is None:
        from config import get_config

        cfg = get_config()
        _engine = create_engine(
            cfg.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory():
    """返回 sessionmaker 工厂（懒加载）。"""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionFactory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    上下文管理器：提供数据库 session，自动 commit/rollback/close。

    用法::

        with get_session() as session:
            session.add(obj)
    """
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """
    创建所有表（CREATE TABLE IF NOT EXISTS）。
    应在应用启动时调用一次。
    """
    Base.metadata.create_all(bind=get_engine(), checkfirst=True)


def reset_engine() -> None:
    """重置缓存的 engine 和 session 工厂（主要用于测试）。"""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
        _engine = None
    _SessionFactory = None
