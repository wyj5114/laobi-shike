import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


spec = importlib.util.spec_from_file_location(
    'task_recovery_test_module',
    Path(__file__).resolve().parents[1] / 'app/services/task_recovery.py',
)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class TaskRecoveryTests(unittest.TestCase):
    def test_timeout_recovers_with_bounded_backoff(self):
        action = Mock(side_effect=[TimeoutError('timed out'), ConnectionError('connection reset'), 'ok'])
        notify = Mock()
        with patch.object(recovery.time, 'sleep') as sleep:
            self.assertEqual(recovery.run_with_retry(action, notify), 'ok')
        self.assertEqual(action.call_count, 3)
        self.assertEqual([call.args for call in sleep.call_args_list], [(2,), (5,)])
        self.assertEqual([call.args for call in notify.call_args_list], [(2, 2), (3, 5)])

    def test_persistent_network_failure_stops_after_three_attempts(self):
        action = Mock(side_effect=TimeoutError('timed out'))
        with patch.object(recovery.time, 'sleep'), self.assertRaises(TimeoutError):
            recovery.run_with_retry(action, Mock())
        self.assertEqual(action.call_count, 3)

    def test_authentication_and_no_speech_errors_are_not_retried(self):
        for error in [ValueError('HTTP Error 403: Forbidden'), recovery.NoSpeechError('未识别到有效语音')]:
            action = Mock(side_effect=error)
            with self.assertRaises(type(error)):
                recovery.run_with_retry(action, Mock())
            action.assert_called_once()

    def test_bcut_temporary_failure_recovers(self):
        action = Mock(side_effect=[Exception('B站ASR任务失败，状态码: 3'), 'transcript'])
        with patch.object(recovery.time, 'sleep'):
            self.assertEqual(recovery.run_with_retry(action, Mock()), 'transcript')
        self.assertEqual(action.call_count, 2)


if __name__ == '__main__':
    unittest.main()
