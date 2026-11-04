"""媒体文件管理：列出下载的视频/音频/截图，并支持清理释放磁盘。"""
import shutil
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter

from app.utils.path_helper import get_data_dir
from app.utils.response import ResponseWrapper as R

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VIDEO_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".flv"}
AUDIO_SUFFIXES = {".m4a", ".mp3", ".wav", ".flac", ".aac", ".ogg"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _roots() -> List[Path]:
    return [
        Path(get_data_dir()).resolve(),
        (PROJECT_ROOT / "uploads").resolve(),
        (PROJECT_ROOT / "static" / "screenshots").resolve(),
    ]


def _kind(suffix: str) -> str | None:
    suffix = suffix.lower()
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in AUDIO_SUFFIXES:
        return "audio"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    return None


def _url_for(path: Path) -> str:
    for root in _roots():
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if root.name == "screenshots":
            return f"/static/screenshots/{relative.as_posix()}"
        if root.name == "uploads":
            return f"/uploads/{relative.as_posix()}"
        return f"/media/{relative.as_posix()}"
    return ""


def _scan() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen = set()
    for root in _roots():
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            kind = _kind(path.suffix)
            if not kind:
                continue
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            stat = path.stat()
            items.append(
                {
                    "path": path.relative_to(PROJECT_ROOT).as_posix(),
                    "name": path.name,
                    "kind": kind,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "url": _url_for(path),
                }
            )
    items.sort(key=lambda item: item["modified"], reverse=True)
    return items


@router.get("/media")
def list_media():
    try:
        items = _scan()
        return R.success(
            data={
                "items": items,
                "count": len(items),
                "total_size": sum(item["size"] for item in items),
            }
        )
    except Exception as exc:
        return R.error(msg=exc)


@router.delete("/media")
def clean_all_media():
    try:
        deleted = 0
        freed = 0
        for root in _roots():
            if not root.exists():
                continue
            for path in list(root.rglob("*")):
                if not path.is_file() or not _kind(path.suffix):
                    continue
                try:
                    freed += path.stat().st_size
                    path.unlink()
                    deleted += 1
                except OSError:
                    continue
        return R.success(data={"deleted": deleted, "freed": freed}, msg="已清理媒体文件")
    except Exception as exc:
        return R.error(msg=exc)


@router.delete("/media/{file_path:path}")
def delete_media(file_path: str):
    try:
        target = (PROJECT_ROOT / file_path).resolve()
        allowed = False
        for root in _roots():
            try:
                target.relative_to(root)
                allowed = True
                break
            except ValueError:
                continue
        if not allowed or not target.is_file():
            return R.error(msg="文件不存在或不允许删除", code=404)
        size = target.stat().st_size
        target.unlink()
        return R.success(data={"freed": size}, msg="已删除")
    except Exception as exc:
        return R.error(msg=exc)
