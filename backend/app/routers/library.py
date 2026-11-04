import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db import library_dao
from app.utils.response import ResponseWrapper as R

router = APIRouter()


class GroupCreateRequest(BaseModel):
    name: str


class GroupUpdateRequest(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None


class NoteGroupRequest(BaseModel):
    group_id: Optional[str] = None


class NoteImportRequest(BaseModel):
    notes: List[Dict[str, Any]]


@router.get("/groups")
def list_groups():
    try:
        return R.success(data=library_dao.list_groups())
    except Exception as exc:
        return R.error(msg=exc)


@router.post("/groups")
def create_group(data: GroupCreateRequest):
    try:
        return R.success(data=library_dao.create_group(data.name), msg="分组已创建")
    except ValueError as exc:
        return R.error(msg=exc, code=400)
    except Exception as exc:
        return R.error(msg=exc)


@router.patch("/groups/{group_id}")
def update_group(group_id: str, data: GroupUpdateRequest):
    try:
        return R.success(data=library_dao.update_group(group_id, data.name, data.order), msg="分组已更新")
    except LookupError as exc:
        return R.error(msg=exc, code=404)
    except ValueError as exc:
        return R.error(msg=exc, code=400)
    except Exception as exc:
        return R.error(msg=exc)


@router.delete("/groups/{group_id}")
def delete_group(group_id: str):
    try:
        library_dao.delete_group(group_id)
        return R.success(msg="分组已删除")
    except LookupError as exc:
        return R.error(msg=exc, code=404)
    except Exception as exc:
        return R.error(msg=exc)


@router.get("/notes")
def list_notes(
    q: Optional[str] = None,
    group_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    try:
        items, total = library_dao.list_notes(q, group_id, status, page, page_size)
        return R.success(data={"items": items, "total": total, "page": page, "page_size": page_size})
    except Exception as exc:
        return R.error(msg=exc)


def _clean_export_title(raw: str) -> str:
    text = re.sub(r"《([^》]+)》", r"\1", raw or "")
    text = re.sub(r"[【\[][^】\]]*[】\]]\s*", "", text)
    text = re.sub(r"全程教学视频|教学视频|完整版|高清|1080P|4K", "", text, flags=re.I)
    text = re.sub(r"p0*\d+\s*", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "未命名笔记"


@router.get("/notes/export")
def export_notes(group_id: Optional[str] = None):
    """把一个分组的所有笔记打包为 ZIP 下载。"""
    try:
        query_group = "ungrouped" if group_id in (None, "", "ungrouped") else group_id
        items: List[Dict[str, Any]] = []
        page = 1
        while True:
            page_items, total = library_dao.list_notes(None, query_group, None, page, 200)
            items.extend(page_items)
            if len(items) >= total or not page_items:
                break
            page += 1

        group_name = "未分组"
        for group in library_dao.list_groups():
            if group["id"] == group_id:
                group_name = group["name"]
                break

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            used = set()
            written = 0
            for item in items:
                note = library_dao.get_note(item["id"])
                markdown = (note or {}).get("markdown") or ""
                if not markdown.strip():
                    continue
                safe_title = re.sub(r'[\\/:*?"<>|]', " ", _clean_export_title(item.get("title") or item["id"]))
                safe_title = re.sub(r"\s+", " ", safe_title).strip() or item["id"]
                filename = f"{safe_title}.md"
                if filename in used:
                    filename = f"{safe_title}-{item['id'][:6]}.md"
                used.add(filename)
                archive.writestr(filename, markdown.strip() + "\n")
                written += 1
        if not written:
            return R.error(msg="该分组没有可导出的笔记正文", code=404)
        buffer.seek(0)
        filename = quote(f"{group_name}-笔记.zip")
        return StreamingResponse(
            buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
        )
    except Exception as exc:
        return R.error(msg=exc)


@router.post("/notes/import")
def import_notes(data: NoteImportRequest):
    try:
        imported = 0
        for item in data.notes:
            task_id = item.get("task_id") or item.get("id")
            if not task_id:
                continue
            library_dao.upsert_note(
                task_id,
                {
                    "video_id": item.get("video_id"),
                    "title": item.get("title"),
                    "duration": item.get("duration"),
                    "cover_url": item.get("cover_url"),
                    "status": item.get("status", "SUCCESS"),
                    "group_id": item.get("group_id"),
                },
            )
            if item.get("markdown") or item.get("transcript"):
                result_path = Path(library_dao.NOTE_OUTPUT_DIR) / f"{task_id}.json"
                result_path.parent.mkdir(parents=True, exist_ok=True)
                result_path.write_text(
                    json.dumps(
                        {
                            "markdown": item.get("markdown", ""),
                            "transcript": item.get("transcript", {}),
                            "audio_meta": item.get("audio_meta", {}),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            imported += 1
        return R.success(data={"imported": imported}, msg="导入完成")
    except Exception as exc:
        return R.error(msg=exc)


@router.get("/notes/{task_id}")
def get_note(task_id: str):
    try:
        note = library_dao.get_note(task_id)
        if not note:
            return R.error(msg="笔记不存在", code=404)
        return R.success(data=note)
    except Exception as exc:
        return R.error(msg=exc)


@router.patch("/notes/{task_id}")
def update_note_group(task_id: str, data: NoteGroupRequest):
    try:
        return R.success(data=library_dao.update_note_group(task_id, data.group_id), msg="已移动")
    except LookupError as exc:
        return R.error(msg=exc, code=404)
    except ValueError as exc:
        return R.error(msg=exc, code=400)
    except Exception as exc:
        return R.error(msg=exc)


@router.delete("/notes/{task_id}")
def delete_note(task_id: str):
    try:
        library_dao.delete_note(task_id)
        return R.success(msg="笔记已删除")
    except LookupError as exc:
        return R.error(msg=exc, code=404)
    except Exception as exc:
        return R.error(msg=exc)
