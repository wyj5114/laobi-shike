"""网络地址小工具：识别本机推理服务（Ollama / LM Studio / vLLM 等）。"""

from typing import Optional
from urllib.parse import urlparse

# 这些 host 视为「本机服务」：OpenAI 兼容但通常不校验 API Key
LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "host.docker.internal",
}


def is_local_base_url(base_url: Optional[str]) -> bool:
    """判断 base_url 是否指向本机（不含端口判断，端口随意）。"""
    if not base_url:
        return False
    try:
        host = (urlparse(str(base_url)).hostname or "").strip().lower()
    except Exception:
        return False
    return host in LOCAL_HOSTS
