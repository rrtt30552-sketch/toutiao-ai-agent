"""AI 客户端：统一 API 调用层，支持多模型切换。"""

import json
import os
import time
from typing import Optional

import requests

from modules.logger import log_info, log_ok, log_warn, log_err

_API_KEY_CACHE: Optional[str] = None
_BASE_URL_CACHE: Optional[str] = None
_LAST_REQUEST_TIME: float = 0.0

DEFAULT_MODEL = "mimo-v2.5"
DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
MAX_RETRIES = 3
TIMEOUT = 120
REQUEST_INTERVAL = 1.0

STEP = "ai"

ENV_API_KEY = "AI_API_KEY"
ENV_BASE_URL = "AI_API_BASE_URL"
ENV_MODEL = "AI_MODEL"


def _load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip("\"'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception as e:
        log_warn(STEP, f"读取 .env 失败: {e}")


_load_dotenv()


def _is_mimo_api() -> bool:
    url = _resolve_base_url().lower()
    return "xiaomimimo" in url


def _resolve_base_url() -> str:
    global _BASE_URL_CACHE
    if _BASE_URL_CACHE:
        return _BASE_URL_CACHE
    url = os.environ.get(ENV_BASE_URL, "").strip()
    if url:
        _BASE_URL_CACHE = url.rstrip("/") + "/chat/completions"
    else:
        _BASE_URL_CACHE = DEFAULT_BASE_URL.rstrip("/") + "/chat/completions"
    return _BASE_URL_CACHE


def resolve_api_key(cli_key: Optional[str] = None) -> str:
    global _API_KEY_CACHE
    if cli_key:
        _API_KEY_CACHE = cli_key
        return cli_key
    if _API_KEY_CACHE:
        return _API_KEY_CACHE
    key = os.environ.get(ENV_API_KEY, os.environ.get("MIMO_API_KEY", "")).strip()
    if key:
        _API_KEY_CACHE = key
        return key
    log_err(STEP, "未找到 API Key。请配置 .env 文件")
    raise RuntimeError("Missing AI_API_KEY")


def _get_model() -> str:
    return os.environ.get(ENV_MODEL, os.environ.get("MIMO_MODEL", DEFAULT_MODEL))


def _build_headers(key: str) -> dict:
    if _is_mimo_api():
        return {"Content-Type": "application/json", "api-key": key}
    return {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}


def _build_payload(prompt: str, max_tokens: int, model: str) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if _is_mimo_api():
        payload["max_completion_tokens"] = max_tokens
    else:
        payload["max_tokens"] = max_tokens
    return payload


def _rate_limit():
    global _LAST_REQUEST_TIME
    elapsed = time.time() - _LAST_REQUEST_TIME
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _LAST_REQUEST_TIME = time.time()


def call_ai(
    prompt: str,
    max_tokens: int = 4096,
    timeout: int = TIMEOUT,
    api_key: Optional[str] = None,
) -> str:
    key = resolve_api_key(api_key)
    model = _get_model()
    api_url = _resolve_base_url()

    headers = _build_headers(key)
    payload = _build_payload(prompt, max_tokens, model)

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        _rate_limit()
        try:
            log_info(STEP, f"调用中 (第 {attempt}/{MAX_RETRIES} 次) [model={model}]")
            t0 = time.time()
            resp = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
            elapsed = time.time() - t0
            result = resp.json()

            if "choices" in result and result["choices"]:
                msg = result["choices"][0].get("message", {})
                content = msg.get("content")

                if content is None or content.strip() == "":
                    finish = result["choices"][0].get("finish_reason", "")
                    log_warn(STEP, f"模型返回空内容 (finish_reason={finish})")
                    last_err = RuntimeError(f"Empty content (finish_reason={finish})")
                    continue

                usage = result.get("usage", {})
                log_ok(STEP, f"调用成功 [{elapsed:.1f}s | tokens={usage.get('total_tokens', '?')}]")
                return content.strip()

            err_msg = result.get("error", {}).get(
                "message", json.dumps(result, ensure_ascii=False)[:300]
            )
            log_warn(STEP, f"API 返回异常: {err_msg}")
            last_err = RuntimeError(f"API error: {err_msg}")

        except requests.exceptions.Timeout:
            log_warn(STEP, f"请求超时 ({timeout}s)")
            last_err = RuntimeError("Request timeout")
        except requests.exceptions.ConnectionError as e:
            log_warn(STEP, f"连接失败: {e}")
            last_err = RuntimeError(f"Connection error: {e}")
        except Exception as e:
            log_warn(STEP, f"未知错误: {e}")
            last_err = RuntimeError(f"Unknown error: {e}")

        if attempt < MAX_RETRIES:
            wait = 2 ** attempt
            log_info(STEP, f"等待 {wait}s 后重试...")
            time.sleep(wait)

    log_err(STEP, f"调用失败（已重试 {MAX_RETRIES} 次）")
    raise last_err


def call_ai_safe(prompt: str, fallback: str = "", **kwargs) -> str:
    try:
        return call_ai(prompt, **kwargs)
    except Exception as e:
        log_err(STEP, f"call_ai_safe 捕获异常: {e}")
        return fallback


def test_connection(api_key: Optional[str] = None) -> bool:
    try:
        result = call_ai(
            "请直接回复'连接成功'四个字，不要解释。",
            max_tokens=500,
            api_key=api_key,
        )
        if result and len(result) > 0:
            log_ok(STEP, f"连接测试通过: {result[:50]}")
            return True
        else:
            log_err(STEP, "连接测试失败: 返回内容为空")
            return False
    except Exception as e:
        log_err(STEP, f"连接测试失败: {e}")
        return False
