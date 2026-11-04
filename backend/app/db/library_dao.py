"""笔记库 / 自定义分组的数据访问层。"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func

from app.db.engine import SessionLocal
from app.db.models.note_groups import NoteGroup
from app.db.models.video_tasks import VideoTask
from app.utils.logger import get_logger

logger = get_logger(__name__)

NOTE_OUTPUT_DIR = Path(os.getenv("NOTE_OUTPUT_DIR", "note_results"))


def _iso(value) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return str(value)


def _note_dict(task: VideoTask) -> Dict[str, Any]:
    return {
        "id": task.task_id,
        "video_id": task.video_id,
        "platform": task.platform,
        "title": task.title or "未命名笔记",
        "duration": task.duration or 0,
        "cover_url": task.cover_url,
        "group_id": task.group_id,
        "status": task.status or "SUCCESS",
        "created_at": _iso(task.created_at),
        "updated_at": _iso(task.updated_at),
    }


def list_groups() -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        groups = db.query(NoteGroup).order_by(NoteGroup.sort_order, NoteGroup.created_at).all()
        counts = {
            group_id: count
            for group_id, count in db.query(VideoTask.group_id, func.count(VideoTask.id))
            .filter(VideoTask.group_id.isnot(None))
            .group_by(VideoTask.group_id)
            .all()
        }
        return [
            {
                "id": group.id,
                "name": group.name,
                "order": group.sort_order,
                "count": counts.get(group.id, 0),
            }
            for group in groups
        ]
    finally:
        db.close()


def existing_video_ids() -> set:
    """返回已存在任务的 video_id，用于批量生成时跳过。"""
    db = SessionLocal()
    try:
        return {row[0] for row in db.query(VideoTask.video_id).all() if row[0]}
    finally:
        db.close()


def create_group(name: str) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise ValueError("分组名不能为空")
    if len(name) > 20:
        raise ValueError("分组名最多 20 个字符")

    db = SessionLocal()
    try:
        if db.query(NoteGroup).filter(NoteGroup.name == name).first():
            raise ValueError("已有同名分组")
        max_order = db.query(func.max(NoteGroup.sort_order)).scalar() or 0
        group = NoteGroup(id=uuid.uuid4().hex, name=name, sort_order=max_order + 1)
        db.add(group)
        db.commit()
        db.refresh(group)
        return {"id": group.id, "name": group.name, "order": group.sort_order, "count": 0}
    finally:
        db.close()


def update_group(group_id: str, name: Optional[str] = None, order: Optional[int] = None) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        group = db.query(NoteGroup).filter(NoteGroup.id == group_id).first()
        if not group:
            raise LookupError("分组不存在")
        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("分组名不能为空")
            duplicate = db.query(NoteGroup).filter(NoteGroup.name == name, NoteGroup.id != group_id).first()
            if duplicate:
                raise ValueError("已有同名分组")
            group.name = name
        if order is not None:
            group.sort_order = order
        db.commit()
        db.refresh(group)
        count = db.query(VideoTask).filter(VideoTask.group_id == group.id).count()
        return {"id": group.id, "name": group.name, "order": group.sort_order, "count": count}
    finally:
        db.close()


def delete_group(group_id: str) -> None:
    db = SessionLocal()
    try:
        group = db.query(NoteGroup).filter(NoteGroup.id == group_id).first()
        if not group:
            raise LookupError("分组不存在")
        db.query(VideoTask).filter(VideoTask.group_id == group_id).update({VideoTask.group_id: None})
        db.delete(group)
        db.commit()
    finally:
        db.close()


def list_notes(
    q: Optional[str] = None,
    group_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    db = SessionLocal()
    try:
        query = db.query(VideoTask)
        if q:
            like = f"%{q.strip()}%"
            query = query.filter(VideoTask.title.ilike(like))
        if group_id == "ungrouped":
            query = query.filter(VideoTask.group_id.is_(None))
        elif group_id:
            query = query.filter(VideoTask.group_id == group_id)
        if status:
            query = query.filter(VideoTask.status == status)

        total = query.count()
        rows = (
            query.order_by(VideoTask.created_at.desc())
            .offset(max(0, (page - 1) * page_size))
            .limit(max(1, min(page_size, 200)))
            .all()
        )
        return [_note_dict(row) for row in rows], total
    finally:
        db.close()


def get_note(task_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.task_id == task_id).first()
        if not task:
            return None
        data = _note_dict(task)
        result_path = NOTE_OUTPUT_DIR / f"{task_id}.json"
        if result_path.exists():
            try:
                content = json.loads(result_path.read_text(encoding="utf-8"))
                data.update(
                    {
                        "markdown": content.get("markdown", ""),
                        "transcript": content.get("transcript", {}),
                        "audio_meta": content.get("audio_meta", {}),
                    }
                )
            except Exception as exc:
                logger.warning(f"读取笔记内容失败 {result_path}: {exc}")
        return data
    finally:
        db.close()


def set_note_status(task_id: str, status: str) -> bool:
    """只更新已存在的任务状态，避免内部缓存 ID（xxx_markdown）生成记录。"""
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.task_id == task_id).first()
        if not task:
            return False
        task.status = status
        db.commit()
        return True
    finally:
        db.close()


def update_note_group(task_id: str, group_id: Optional[str]) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.task_id == task_id).first()
        if not task:
            raise LookupError("笔记不存在")
        if group_id and not db.query(NoteGroup).filter(NoteGroup.id == group_id).first():
            raise ValueError("分组不存在")
        task.group_id = group_id or None
        db.commit()
        db.refresh(task)
        return _note_dict(task)
    finally:
        db.close()


def delete_note(task_id: str) -> None:
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.task_id == task_id).first()
        if not task:
            raise LookupError("笔记不存在")
        db.delete(task)
        db.commit()
    finally:
        db.close()

    for suffix in (".json", ".status.json", "_audio.json", "_transcript.json", "_markdown.md"):
        path = NOTE_OUTPUT_DIR / f"{task_id}{suffix}"
        if path.exists():
            try:
                path.unlink()
            except OSError as exc:
                logger.warning(f"删除笔记文件失败 {path}: {exc}")


def upsert_note(task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """供生成任务保存元数据 / 旧数据导入使用。"""
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.task_id == task_id).first()
        if not task:
            task = VideoTask(task_id=task_id, video_id=payload.get("video_id") or task_id, platform="bilibili")
            db.add(task)
        task.video_id = payload.get("video_id") or task.video_id or task_id
        task.title = payload.get("title") or task.title
        task.duration = int(payload.get("duration") or task.duration or 0)
        task.cover_url = payload.get("cover_url") or task.cover_url
        task.status = payload.get("status") or task.status or "SUCCESS"
        if "group_id" in payload:
            task.group_id = payload.get("group_id")
        db.commit()
        db.refresh(task)
        return _note_dict(task)
    finally:
        db.close()
