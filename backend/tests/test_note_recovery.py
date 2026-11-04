import json
from unittest.mock import Mock

from fastapi import BackgroundTasks
import pytest

from app.models.transcriber_model import TranscriptResult, TranscriptSegment
from app.routers import note as router
from app.services.note import NoteGenerator
from app.services.task_recovery import NoSpeechError
from app.services.transcriber_config_manager import TranscriberConfigManager
from app.enmus.task_status_enums import TaskStatus


def test_empty_transcript_does_not_call_summary_model(tmp_path):
    generator = NoteGenerator.__new__(NoteGenerator)
    gpt = Mock()
    with pytest.raises(NoSpeechError, match='未识别到有效语音'):
        generator._summarize_text(
            None, TranscriptResult('zh', '', []), gpt,
            tmp_path / 'empty_markdown.md', False, False, [], None, None, [],
        )
    gpt.summarize.assert_not_called()


def test_empty_cached_transcript_is_replaced_by_new_recognition(tmp_path):
    cache = tmp_path / 'task_transcript.json'
    cache.write_text(json.dumps({'language': 'zh', 'full_text': '', 'segments': []}))
    generator = NoteGenerator.__new__(NoteGenerator)
    generator._update_status = Mock()
    generator._handle_exception = Mock()
    generator.transcriber = Mock()
    generator.transcriber.transcript.return_value = TranscriptResult('zh', '有效语音', [TranscriptSegment(0, 1, '有效语音')])
    result = generator._transcribe_audio('audio.m4a', cache, TaskStatus.TRANSCRIBING)
    assert result.full_text == '有效语音'
    generator.transcriber.transcript.assert_called_once()
    assert json.loads(cache.read_text(encoding='utf-8'))['segments']


def test_full_text_without_timestamps_is_preserved():
    result = NoteGenerator._validate_transcript(TranscriptResult('zh', '有效语音', []))
    assert result.segments[0].text == '有效语音'


def test_retry_keeps_original_part_and_rejects_duplicate(tmp_path, monkeypatch):
    task_id = '00000000-0000-0000-0000-000000000123'
    monkeypatch.setattr(router, 'NOTE_OUTPUT_DIR', str(tmp_path))
    monkeypatch.setenv('NOTE_OUTPUT_DIR', str(tmp_path))
    monkeypatch.setattr(router, 'get_note', lambda _: {'video_id': 'BV1DMxj6wEEN', 'status': 'FAILED'})
    monkeypatch.setattr(TranscriberConfigManager, 'is_model_ready', lambda _: {'ready': True})
    request = router.VideoRequest(
        task_id=task_id, video_url='https://www.bilibili.com/video/BV1DMxj6wEEN?p=22',
        platform='bilibili', quality='medium', model_name='test-model', provider_id='test-provider',
    )
    router.run_note_task(
        task_id, request.video_url, request.platform, request.quality,
        model_name=request.model_name, provider_id=request.provider_id,
        executor=Mock(run=Mock(return_value=None)),
    )
    snapshot = json.loads((tmp_path / f'{task_id}.request.json').read_text(encoding='utf-8'))
    assert snapshot['video_url'].endswith('?p=22')
    assert 'api_key' not in snapshot
    (tmp_path / f'{task_id}.status.json').write_text('{"status":"FAILED"}')
    queue = BackgroundTasks()
    assert json.loads(router.generate_note(request, queue).body)['code'] == 0
    assert json.loads(router.generate_note(request, queue).body)['code'] == 409
    assert len(queue.tasks) == 1


def test_retry_cannot_reuse_cache_for_another_part(tmp_path, monkeypatch):
    task_id = '00000000-0000-0000-0000-000000000124'
    monkeypatch.setattr(router, 'NOTE_OUTPUT_DIR', str(tmp_path))
    monkeypatch.setattr(router, 'get_note', lambda _: {'video_id': 'BV1DMxj6wEEN', 'status': 'FAILED'})
    monkeypatch.setattr(TranscriberConfigManager, 'is_model_ready', lambda _: {'ready': True})
    (tmp_path / f'{task_id}.request.json').write_text(json.dumps({'video_url': 'https://www.bilibili.com/video/BV1DMxj6wEEN?p=22'}))
    queue = BackgroundTasks()
    request = router.VideoRequest(task_id=task_id, video_url='https://www.bilibili.com/video/BV1DMxj6wEEN?p=24', platform='bilibili', quality='medium', model_name='test', provider_id='test')
    assert json.loads(router.generate_note(request, queue).body)['code'] == 400
    assert not queue.tasks
