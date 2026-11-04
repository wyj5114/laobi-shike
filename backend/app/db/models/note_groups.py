from sqlalchemy import Column, Integer, String, DateTime, func

from app.db.engine import Base


class NoteGroup(Base):
    __tablename__ = "note_groups"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
