"""统一构造 OpenAI 兼容客户端：注入全局代理 + 校验 api_key。

为什么要这一层：
  - 代理：openai SDK 默认只认进程级 HTTP_PROXY 环境变量，桌面端用户在 UI 里
    填的代理需要显式塞进 httpx.Client 才生效。
  - api_key 校验：空 key 会让 httpx 拼出非法 header `Bearer `，抛出
    `httpx.LocalProtocolError: Illegal header value b'Bearer '` 这种天书报错。
    在入口挡掉，给用户「xxx 的 API Key 未配置」这种能看懂的提示。
"""
from typing import Optional

from openai import OpenAI

from app.services.proxy_config_manager import ProxyConfigManager
from app.utils.logger import get_logger
from app.utils.net_helper import is_local_base_url

logger = get_logger(__name__)


def build_openai_client(
    api_key: Optional[str],
    base_url: Optional[str],
    *,
    key_label: str = "API Key",
    timeout: Optional[float] = None,
) -> OpenAI:
    """构造 OpenAI 客户端。api_key 为空直接抛清晰错误；代理已配置则注入。

    key_label 用于错误提示，例如 "Groq 的 API Key" / "OpenAI 供应商的 API Key"。

    例外：base_url 指向本机（Ollama / LM Studio / vLLM）时，空 key 用占位符 "ollama"。
    这些服务本身不校验 key，但 OpenAI SDK 会拼出非法的 `Bearer ` 头，必须给个非空值。
    """
    key = (api_key or "").strip()
    if not key:
        if is_local_base_url(base_url):
            key = "ollama"
            logger.info("本机推理服务未配置 API Key，使用占位 key（%s）", base_url)
        else:
            raise ValueError(f"{key_label} 未配置，请先在「设置」里填写后再使用")

    kwargs = {"api_key": key, "base_url": base_url}
    if timeout is not None:
        kwargs["timeout"] = timeout

    proxy_url = ProxyConfigManager().get_proxy_url()
    if proxy_url:
        # 延迟 import httpx：仅在确实要走代理时才需要
        import httpx
        kwargs["http_client"] = httpx.Client(proxy=proxy_url, timeout=timeout or 600.0)
        logger.info(f"OpenAI 客户端走代理: {proxy_url}")

    return OpenAI(**kwargs)
