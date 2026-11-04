"""任务状态文件读写。

独立于 NoteGenerator，避免为了写一个 PENDING 状态就加载转写器/模型。
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from app.enmus.task_status_enums import TaskStatus


def _status_dir(output_dir: Optional[Union[str, Path]] = None) -> Path:
    return Path(output_dir or os.getenv("NOTE_OUTPUT_DIR", "note_results"))


def update_status(
    task_id: Optional[str],
    status: Union[str, TaskStatus],
    message: Optional[str] = None,
    output_dir: Optional[Union[str, Path]] = None,
) -> None:
    """原子写入 `{task_id}.status.json`，并保留真实阶段日志。"""
    if not task_id:
        return

    base = _status_dir(output_dir)
    base.mkdir(parents=True, exist_ok=True)

    status_value = status.value if isinstance(status, TaskStatus) else status
    status_file = base / f"{task_id}.status.json"

    existing: dict = {}
    if status_file.exists():
        try:
            existing = json.loads(status_file.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    logs = list(existing.get("logs") or [])
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "status": status_value,
        "message": message or "",
    }
    if not logs or logs[-1].get("status") != status_value or (
        message and logs[-1].get("message") != message
    ):
        logs.append(entry)

    payload = {
        "status": status_value,
        "logs": logs[-200:],
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if message:
        payload["message"] = message

    temp_file = status_file.with_suffix(".tmp")
    temp_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_file.replace(status_file)
