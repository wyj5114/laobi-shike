"""P0 下载调优：分片并发、去掉 mp3 转码、截图视频限 720p。"""
import importlib.util
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "app" / "downloaders" / "base.py"
BILI_PATH = ROOT / "app" / "downloaders" / "bilibili_downloader.py"


def _stub(monkeypatch, name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)


def _load_base(monkeypatch):
    _stub(monkeypatch, "app")
    _stub(monkeypatch, "app.enmus")
    _stub(monkeypatch, "app.models")
    _stub(monkeypatch, "app.enmus.note_enums", DownloadQuality=str)
    _stub(monkeypatch, "app.models.notes_model", AudioDownloadResult=object)
    _stub(monkeypatch, "app.models.transcriber_model", TranscriptResult=object)
    spec = importlib.util.spec_from_file_location("dl_base_under_test", BASE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_retry_opts_enable_parallel_fragments(monkeypatch):
    base = _load_base(monkeypatch)
    assert base.YDL_RETRY_OPTS["concurrent_fragment_downloads"] >= 2


class _AudioResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeYDL:
    calls = []
    tmp_dir = None

    def __init__(self, options):
        self.options = options
        type(self).calls.append(options)
        self._tmp = options.get("__tmp")

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def extract_info(self, _url, download=True):
        if type(self).tmp_dir:
            import os

            with open(os.path.join(type(self).tmp_dir, "vid.mp4"), "wb"):
                pass
        return {
            "id": "vid",
            "title": "Example",
            "duration": 12,
            "thumbnail": None,
            "ext": "m4a",
        }


def _load_bilibili(monkeypatch, tmp_path):
    _stub(monkeypatch, "app")
    _stub(monkeypatch, "app.downloaders")
    _stub(monkeypatch, "app.models")
    _stub(monkeypatch, "app.services")
    _stub(monkeypatch, "app.utils")
    _stub(
        monkeypatch,
        "app.downloaders.base",
        Downloader=type("Downloader", (), {"__init__": lambda self: setattr(self, "cache_data", str(tmp_path))}),
        DownloadQuality=str,
        YDL_RETRY_OPTS={"retries": 3, "fragment_retries": 3, "socket_timeout": 30, "concurrent_fragment_downloads": 4},
        QUALITY_MAP={"fast": "32", "medium": "64", "slow": "128"},
    )
    _stub(monkeypatch, "app.downloaders.bilibili_dm_patch", apply_bilibili_dm_img_patch=lambda: True)
    _stub(monkeypatch, "app.downloaders.bilibili_subtitle", BilibiliSubtitleFetcher=object)
    _stub(monkeypatch, "app.models.notes_model", AudioDownloadResult=_AudioResult)
    _stub(monkeypatch, "app.models.transcriber_model", TranscriptResult=object, TranscriptSegment=object)
    _stub(monkeypatch, "app.utils.path_helper", get_data_dir=lambda: str(tmp_path))
    _stub(monkeypatch, "app.utils.url_parser", extract_video_id=lambda url, platform: "vid")
    _stub(
        monkeypatch,
        "app.services.cookie_manager",
        CookieConfigManager=type("CookieConfigManager", (), {"get": lambda self, _platform: None}),
    )
    _stub(monkeypatch, "yt_dlp", YoutubeDL=_FakeYDL)
    spec = importlib.util.spec_from_file_location("bilibili_under_test", BILI_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_audio_download_skips_mp3_transcode(monkeypatch, tmp_path):
    _FakeYDL.calls.clear()
    module = _load_bilibili(monkeypatch, tmp_path)
    downloader = module.BilibiliDownloader()
    result = downloader.download("https://www.bilibili.com/video/BV1xx", output_dir=str(tmp_path))

    options = _FakeYDL.calls[-1]
    assert "postprocessors" not in options
    assert options["concurrent_fragment_downloads"] >= 2
    assert result.file_path.endswith(".m4a")


def test_audio_quality_maps_to_bitrate_cap(monkeypatch, tmp_path):
    _FakeYDL.calls.clear()
    module = _load_bilibili(monkeypatch, tmp_path)
    downloader = module.BilibiliDownloader()

    downloader.download("https://www.bilibili.com/video/BV1xx", output_dir=str(tmp_path), quality="fast")
    assert "abr<=80" in _FakeYDL.calls[-1]["format"]

    downloader.download("https://www.bilibili.com/video/BV1xx", output_dir=str(tmp_path), quality="medium")
    assert "abr<=140" in _FakeYDL.calls[-1]["format"]


def test_audio_download_supports_metadata_only(monkeypatch, tmp_path):
    _FakeYDL.calls.clear()
    module = _load_bilibili(monkeypatch, tmp_path)
    downloader = module.BilibiliDownloader()
    downloader.download(
        "https://www.bilibili.com/video/BV1xx",
        output_dir=str(tmp_path),
        skip_download=True,
    )

    options = _FakeYDL.calls[-1]
    assert options["skip_download"] is True
    assert options["ignore_no_formats_error"] is True


def test_video_download_caps_height_for_screenshots(monkeypatch, tmp_path):
    _FakeYDL.calls.clear()
    _FakeYDL.tmp_dir = str(tmp_path)
    module = _load_bilibili(monkeypatch, tmp_path)
    downloader = module.BilibiliDownloader()
    downloader.download_video("https://www.bilibili.com/video/BV1xx", output_dir=str(tmp_path))

    options = _FakeYDL.calls[-1]
    assert "height<=720" in options["format"]
