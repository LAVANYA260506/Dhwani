"""
Gemini client for the agent. The model is only used to understand what the
applicant said (as JSON); it never writes to the application.

    data = generate_json(system_instruction, user_text)   # -> dict

- Authenticates with the x-goog-api-key header; the key is never logged.
- Asks for JSON output and parses it defensively (code fences, extra text).
- Retries once for timeouts, 429 and 5xx. Bad requests and bad keys are not retried.
- Newer Gemini models reject the old sampling settings (temperature, top_p,
  top_k), so none are sent.
- Failures raise LLMError; the agent then falls back to rule-based extraction.
"""

import json
import logging
import re
import time
from typing import Any

import requests

logger = logging.getLogger("dhwani.agent")


class LLMError(Exception):
    """Any failure talking to the language model."""

    def __init__(self, kind: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.kind = kind  # auth, rate_limit, bad_request, timeout, unavailable, blocked, bad_output, network
        self.message = message
        self.status_code = status_code

    @property
    def retryable(self) -> bool:
        return self.kind in {"rate_limit", "timeout", "unavailable", "network"}

    def __str__(self) -> str:
        return f"LLMError({self.kind}{'/' + str(self.status_code) if self.status_code else ''}): {self.message}"


def _settings():
    from app.config import settings  # imported here to keep this module standalone

    return settings


def _headers() -> dict[str, str]:
    key = _settings().LLM_API_KEY
    if not key:
        raise LLMError("auth", "LLM_API_KEY is not set. Add it to backend/.env.")
    return {"x-goog-api-key": key, "Content-Type": "application/json"}


def _kind_for(status: int, body_text: str) -> str:
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "rate_limit"
    if status in (408, 504):
        return "timeout"
    if status >= 500:
        return "unavailable"
    return "bad_request"


def _error_message(response: requests.Response) -> str:
    try:
        return response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return f"Gemini returned HTTP {response.status_code}."


def _send(method: str, url: str, **kwargs: Any) -> requests.Response:
    settings = _settings()
    attempt = 0
    while True:
        error: LLMError | None = None
        try:
            response = requests.request(
                method, url, headers=_headers(), timeout=settings.LLM_TIMEOUT_SECONDS, **kwargs
            )
            if response.ok:
                return response
            error = LLMError(
                _kind_for(response.status_code, response.text),
                _error_message(response),
                response.status_code,
            )
        except requests.Timeout:
            error = LLMError("timeout", "The language model took too long to answer.")
        except requests.RequestException:
            error = LLMError("network", "Could not reach the language model.")

        logger.warning("gemini %s failed: %s (attempt %d)", method, error, attempt + 1)
        allowed_retries = 2 if error.kind == "rate_limit" else 1
        if error.retryable and attempt < allowed_retries:
            time.sleep(2.5 if error.kind == "rate_limit" else 1.0)
            attempt += 1
            continue
        raise error


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
    except ValueError:
        # Last resort: the first {...} block in the text
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise LLMError("bad_output", "The language model did not return JSON.")
        try:
            data = json.loads(match.group(0))
        except ValueError:
            raise LLMError("bad_output", "The language model returned invalid JSON.")
    if not isinstance(data, dict):
        raise LLMError("bad_output", "The language model returned an unexpected JSON shape.")
    return data


def generate_json(system_instruction: str, user_text: str) -> dict[str, Any]:
    """Ask Gemini for a JSON object."""
    settings = _settings()
    url = f"{settings.LLM_BASE_URL.rstrip('/')}/models/{settings.LLM_MODEL}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    started = time.perf_counter()
    body = _send("POST", url, json=payload).json()
    elapsed = time.perf_counter() - started

    candidates = body.get("candidates") or []
    if not candidates:
        reason = (body.get("promptFeedback") or {}).get("blockReason", "no answer")
        raise LLMError("blocked", f"The language model gave no answer ({reason}).")

    parts = (candidates[0].get("content") or {}).get("parts") or []
    # Skip any "thought" parts some models include; keep the answer text
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if not text.strip():
        raise LLMError("bad_output", "The language model returned an empty answer.")

    logger.info("gemini ok: model=%s, %.2fs", settings.LLM_MODEL, elapsed)
    return _parse_json(text)


def list_models() -> list[dict[str, Any]]:
    """Models this key can use with generateContent (for choosing LLM_MODEL)."""
    settings = _settings()
    url = f"{settings.LLM_BASE_URL.rstrip('/')}/models?pageSize=200"
    models = _send("GET", url).json().get("models", [])
    return [m for m in models if "generateContent" in m.get("supportedGenerationMethods", [])]