from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Boolean, JSON, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def utcnow():
    return datetime.now(timezone.utc)

class WallPostGate(Base):
    """A portable singleton write lock serializes DB posting-quota checks."""
    __tablename__ = 'wall_post_gate'
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=0)

class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100))
    summary: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    tech: Mapped[list] = mapped_column(JSON)
    highlights: Mapped[list] = mapped_column(JSON)
    thumbnail_url: Mapped[str] = mapped_column(Text)
    github_url: Mapped[str] = mapped_column(Text, default='')
    demo_url: Mapped[str] = mapped_column(Text, default='')
    video_id: Mapped[str] = mapped_column(String(100), default='')
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)

class WallMessage(Base):
    __tablename__ = 'wall_messages'
    __table_args__ = (Index('ix_wall_status_created', 'status', 'created_at'), Index('ix_wall_status_likes', 'status', 'like_count'))
    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(24))
    content: Mapped[str] = mapped_column(String(300))
    emoji: Mapped[str | None] = mapped_column(String(16), nullable=True)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default='approved')
    report_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ip_hash: Mapped[str] = mapped_column(String(64))
    visitor_hash: Mapped[str] = mapped_column(String(64))

class WallLike(Base):
    __tablename__ = 'wall_likes'
    __table_args__ = (UniqueConstraint('message_id', 'visitor_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey('wall_messages.id', ondelete='CASCADE'))
    visitor_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class WallReport(Base):
    __tablename__ = 'wall_reports'
    __table_args__ = (UniqueConstraint('message_id', 'reporter_hash'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey('wall_messages.id', ondelete='CASCADE'))
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    reporter_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ContactMessage(Base):
    __tablename__ = 'contact_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ip_hash: Mapped[str] = mapped_column(String(64))
    handled: Mapped[bool] = mapped_column(Boolean, default=False)

class ChatLog(Base):
    __tablename__ = 'chat_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
