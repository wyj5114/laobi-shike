"""笔记库/分组 API 回归测试（独立临时 SQLite）。"""
import os
import pathlib
import subprocess
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_groups_and_notes_roundtrip(tmp_path):
    script = textwrap.dedent(
        """
        import os, sys
        sys.path.insert(0, os.environ["BACKEND_ROOT"])
        from app.db.init_db import init_db
        init_db()
        from app import create_app
        from fastapi.testclient import TestClient

        client = TestClient(create_app(lifespan=None))

        group = client.post("/api/groups", json={"name": "考研数学"}).json()
        assert group["code"] == 0, group
        gid = group["data"]["id"]

        imported = client.post(
            "/api/notes/import",
            json={"notes": [{
                "task_id": "t1",
                "title": "线性代数第 12 讲",
                "duration": 2538,
                "status": "SUCCESS",
                "group_id": gid,
                "markdown": "## 一、测试",
            }]},
        ).json()
        assert imported["code"] == 0, imported

        notes = client.get("/api/notes").json()["data"]
        assert notes["total"] == 1
        assert notes["items"][0]["group_id"] == gid

        detail = client.get("/api/notes/t1").json()["data"]
        assert detail["markdown"] == "## 一、测试"

        moved = client.patch("/api/notes/t1", json={"group_id": None}).json()["data"]
        assert moved["group_id"] is None

        assert client.delete(f"/api/groups/{gid}").json()["code"] == 0
        """
    )
    env = os.environ.copy()
    env["BACKEND_ROOT"] = str(ROOT)
    env["DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"
    env["NOTE_OUTPUT_DIR"] = str(tmp_path / "results")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT), env.get("PYTHONPATH")]))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
