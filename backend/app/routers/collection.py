"""B 站合集 / 多 P / 系列识别。"""
import re
import time
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter

from app.db.library_dao import existing_video_ids
from app.services.cookie_manager import CookieConfigManager
from app.utils.logger import get_logger
from app.utils.response import ResponseWrapper as R
from app.utils.url_parser import extract_video_id, resolve_bilibili_short_url

logger = get_logger(__name__)
router = APIRouter()

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _headers() -> dict:
    headers = {"User-Agent": UA, "Referer": "https://www.bilibili.com"}
    cookie = CookieConfigManager().get("bilibili") or ""
    if cookie:
        headers["Cookie"] = cookie
    return headers


def _get(url: str, params: Optional[dict] = None) -> Optional[dict]:
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, headers=_headers(), timeout=15)
            data = response.json()
            if data.get("code") != 0:
                logger.warning(f"B 站接口错误: {url} code={data.get('code')} msg={data.get('message')}")
                return None
            return data.get("data")
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.6 * (attempt + 1))
    logger.warning(f"B 站接口请求失败: {url} {last_error}")
    return None


def _video_item(
    bvid: str,
    title: str,
    duration: float,
    url: str,
    *,
    page: Optional[int] = None,
    video_id: Optional[str] = None,
    existing: Optional[set] = None,
) -> Dict[str, Any]:
    video_id = video_id or bvid
    return {
        "video_id": video_id,
        "bvid": bvid,
        "page": page,
        "title": title,
        "duration": int(duration or 0),
        "url": url,
        "generated": bool(existing and (video_id in existing or bvid in existing)),
    }


def _from_pages(bvid: str, data: dict, existing: set) -> List[Dict[str, Any]]:
    pages = data.get("pages") or []
    items = []
    for page in pages:
        number = int(page.get("page") or 0)
        items.append(
            _video_item(
                bvid,
                page.get("part") or f"P{number}",
                page.get("duration") or 0,
                f"https://www.bilibili.com/video/{bvid}?p={number}",
                page=number,
                video_id=f"{bvid}_p{number}",
                existing=existing,
            )
        )
    return items


def _from_season(data: dict, existing: set) -> List[Dict[str, Any]]:
    season = data.get("ugc_season") or {}
    items = []
    for section in season.get("sections") or []:
        for episode in section.get("episodes") or []:
            bvid = episode.get("bvid")
            if not bvid:
                continue
            arc = episode.get("arc") or {}
            items.append(
                _video_item(
                    bvid,
                    episode.get("title") or arc.get("title") or bvid,
                    arc.get("duration") or 0,
                    f"https://www.bilibili.com/video/{bvid}",
                    existing=existing,
                )
            )
    return items


def _from_series(mid: str, series_id: str, existing: set) -> List[Dict[str, Any]]:
    data = _get(
        "https://api.bilibili.com/x/series/archives",
        {"mid": mid, "series_id": series_id, "only_unum": 1, "pn": 1, "ps": 100},
    )
    if not data:
        return []
    items = []
    for archive in data.get("archives") or []:
        bvid = archive.get("bvid")
        if not bvid:
            continue
        items.append(
            _video_item(
                bvid,
                archive.get("title") or bvid,
                archive.get("duration") or 0,
                f"https://www.bilibili.com/video/{bvid}",
                existing=existing,
            )
        )
    return items


@router.get("/bilibili/collection")
def get_collection(url: str):
    try:
        if "b23.tv" in url:
            url = resolve_bilibili_short_url(url) or url
        existing = existing_video_ids()

        # UP 主系列：space.bilibili.com/{mid}/lists/{series_id}
        series_match = re.search(r"space\.bilibili\.com/(\d+)/lists/(\d+)", url)
        if series_match:
            items = _from_series(series_match.group(1), series_match.group(2), existing)
            if not items:
                return R.error(msg="没有读取到该系列的视频，请确认链接或 Cookie")
            return R.success({
                "kind": "series",
                "title": "UP 主系列",
                "total": len(items),
                "items": items,
            })

        bvid = extract_video_id(url, "bilibili")
        if not bvid:
            return R.error(msg="没有识别到 BV 号")

        data = _get("https://api.bilibili.com/x/web-interface/view", {"bvid": bvid})
        if not data:
            return R.error(msg="B 站视频信息读取失败")

        title = data.get("title") or bvid
        pages = data.get("pages") or []
        if len(pages) > 1:
            items = _from_pages(bvid, data, existing)
            return R.success({
                "kind": "pages",
                "title": title,
                "total": len(items),
                "items": items,
            })

        if data.get("ugc_season"):
            items = _from_season(data, existing)
            if items:
                return R.success({
                    "kind": "season",
                    "title": data["ugc_season"].get("title") or title,
                    "total": len(items),
                    "items": items,
                })

        return R.success({
            "kind": "single",
            "title": title,
            "total": 1,
            "items": [
                _video_item(
                    bvid,
                    title,
                    data.get("duration") or 0,
                    f"https://www.bilibili.com/video/{bvid}",
                    existing=existing,
                )
            ],
        })
    except Exception as exc:
        logger.error(f"合集识别失败: {exc}", exc_info=True)
        return R.error(msg=f"合集识别失败: {exc}")
