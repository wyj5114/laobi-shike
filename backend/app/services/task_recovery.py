import time
from typing import Callable, TypeVar

T = TypeVar('T')


class NoSpeechError(ValueError):
    pass


def is_temporary_failure(error: Exception) -> bool:
    message = str(error).lower()
    return isinstance(error, (TimeoutError, ConnectionError)) or any(marker in message for marker in (
        'timed out', 'timeout', 'connection reset', 'connection aborted',
        'connection refused', 'temporary failure', 'temporarily unavailable',
        'remote end closed', 'failed to resolve', 'name resolution',
        'getaddrinfo failed', 'network is unreachable',
        'http error 429', 'http error 500', 'http error 502',
        'http error 503', 'http error 504', 'asr任务失败，状态码: 3',
    ))


def run_with_retry(action: Callable[[], T], on_retry: Callable[[int, int], None]) -> T:
    for attempt in range(1, 4):
        try:
            return action()
        except Exception as error:
            if attempt == 3 or not is_temporary_failure(error):
                raise
            delay = 2 if attempt == 1 else 5
            on_retry(attempt + 1, delay)
            time.sleep(delay)
