from sqlalchemy import Column, Integer, String, DateTime, func

from app.db.engine import Base


class VideoTask(Base):
    __tablename__ = "video_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    task_id = Column(String, unique=True, nullable=False)
    group_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=True)
    duration = Column(Integer, default=0)
    cover_url = Column(String, nullable=True)
    status = Column(String, default="SUCCESS")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
