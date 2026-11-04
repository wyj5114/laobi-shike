from app.db.models.models import Model
from app.db.models.note_groups import NoteGroup
from app.db.models.providers import Provider
from app.db.models.video_tasks import VideoTask
from app.db.engine import get_engine, Base


_VIDEO_TASK_COLUMNS = {
    "group_id": "VARCHAR",
    "title": "VARCHAR",
    "duration": "INTEGER DEFAULT 0",
    "cover_url": "VARCHAR",
    "status": "VARCHAR DEFAULT 'SUCCESS'",
    "updated_at": "DATETIME",
}


def _ensure_video_task_columns(engine) -> None:
    """轻量迁移：给已存在的 video_tasks 补齐新列。"""
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as conn:
        existing = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(video_tasks)").fetchall()
        }
        for column, ddl in _VIDEO_TASK_COLUMNS.items():
            if column not in existing:
                conn.exec_driver_sql(f"ALTER TABLE video_tasks ADD COLUMN {column} {ddl}")


def init_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _ensure_video_task_columns(engine)
