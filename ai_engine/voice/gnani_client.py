"""
Gnani HTTP client: the single place that talks to Gnani's speech API.

    client = get_gnani_client()
    response = client.request("POST", "/stt/v3", data={...}, files={...})
    response.json()  /  response.content

- Authenticates with the X-API-Key-ID header. The key is never logged.
- Adds a request ID to every call for tracing.
- Retries once, with a short pause, only for problems that can clear up by
  themselves (timeout, network drop, 429, 5xx). Bad requests, bad keys and
  missing credits are never retried, so credits are not wasted.
- Turns every failure into a GnaniError with a `kind`, so callers can decide
  what to tell the applicant without parsing Gnani's different error formats.
"""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger("dhwani.voice")

DEFAULT_BASE_URL = "https://api.vachana.ai"

# Error kinds
AUTH = "auth"                # missing, invalid or unauthorised key
CREDITS = "credits"          # out of credits
RATE_LIMIT = "rate_limit"    # too many requests (some accounts: one at a time)
BAD_REQUEST = "bad_request"  # invalid parameters, unusable audio, empty text...
TIMEOUT = "timeout"          # no answer in time
UNAVAILABLE = "unavailable"  # Gnani returned a server error
NETWORK = "network"          # could not reach Gnani at all

_RETRYABLE = {TIMEOUT, UNAVAILABLE, NETWORK, RATE_LIMIT}


class GnaniError(Exception):
    """Any failure talking to Gnani."""

    def __init__(
        self,
        kind: str,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        request_id: str | None = None,
    ):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.status_code = status_code
        self.code = code  # Gnani's own error code, e.g. EMPTY_AUDIO
        self.request_id = request_id

    @property
    def retryable(self) -> bool:
        return self.kind in _RETRYABLE

    def __str__(self) -> str:
        parts = [self.kind]
        if self.status_code:
            parts.append(str(self.status_code))
        if self.code:
            parts.append(self.code)
        return f"GnaniError({' / '.join(parts)}): {self.message}"


@dataclass
class GnaniResponse:
    content: bytes
    content_type: str
    request_id: str
    latency_seconds: float

    def json(self) -> Any:
        import json

        try:
            return json.loads(self.content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise GnaniError(
                UNAVAILABLE,
                "Gnani sent a reply that could not be read.",
                request_id=self.request_id,
            ) from exc


def _kind_for(status: int, code: str | None, message: str) -> str:
    if status == 401:
        return AUTH
    if status == 402:
        return CREDITS
    if status == 403:
        # Gnani uses 403 for both a bad scope and no credits left
        return CREDITS if "credit" in message.lower() else AUTH
    if status == 429:
        return RATE_LIMIT
    if status in (408, 504) or code == "UPSTREAM_TIMEOUT":
        return TIMEOUT
    if status >= 500:
        return UNAVAILABLE
    return BAD_REQUEST


def _error_from_response(response: requests.Response, request_id: str) -> GnaniError:
    """Gnani reports errors in several shapes; read them all."""
    status = response.status_code
    code: str | None = None
    message: str | None = None

    try:
        body = response.json()
    except ValueError:
        body = None

    if isinstance(body, dict):
        error = body.get("error")
        detail = body.get("detail")
        if isinstance(error, dict):  # {"success": false, "error": {type, message}}
            code, message = error.get("type"), error.get("message")
        elif isinstance(error, str):  # 504: {"error": "...", "code": "...", "message": "..."}
            code, message = body.get("code"), body.get("message") or error
        elif isinstance(detail, dict):  # {"detail": {"error_code", "message"}}
            code, message = detail.get("error_code"), detail.get("message")
        elif isinstance(detail, list) and detail:  # 422 validation
            first = detail[0] if isinstance(detail[0], dict) else {}
            where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
            code = "VALIDATION_ERROR"
            message = f"{where}: {first.get('msg', 'invalid value')}".strip(": ")

    message = message or f"Gnani returned HTTP {status}."
    return GnaniError(
        _kind_for(status, code, message),
        message,
        status_code=status,
        code=code,
        request_id=request_id,
    )


class GnaniClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        max_retries: int = 1,
    ):
        if not api_key:
            raise GnaniError(AUTH, "GNANI_API_KEY is not set. Add it to backend/.env.")
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> GnaniResponse:
        """Send one request. `files` values must be bytes-based tuples
        (name, bytes, content_type) so a retry can resend them."""
        url = f"{self.base_url}{path}"
        request_id = str(uuid.uuid4())
        headers = {"X-API-Key-ID": self._api_key, "X-API-Request-ID": request_id}

        attempt = 0
        while True:
            started = time.perf_counter()
            error: GnaniError | None = None
            try:
                response = self._session.request(
                    method,
                    url,
                    headers=headers,
                    json=json,
                    data=data,
                    files=files,
                    timeout=self.timeout,
                )
            except requests.Timeout:
                error = GnaniError(
                    TIMEOUT, "The voice service took too long to answer.",
                    request_id=request_id,
                )
            except requests.RequestException:
                error = GnaniError(
                    NETWORK, "Could not reach the voice service.",
                    request_id=request_id,
                )
            else:
                elapsed = time.perf_counter() - started
                if response.ok:
                    logger.info(
                        "gnani %s %s -> %s in %.2fs (request %s)",
                        method, path, response.status_code, elapsed, request_id,
                    )
                    return GnaniResponse(
                        content=response.content,
                        content_type=response.headers.get("Content-Type", ""),
                        request_id=request_id,
                        latency_seconds=elapsed,
                    )
                error = _error_from_response(response, request_id)

            logger.warning(
                "gnani %s %s failed: %s (attempt %d)", method, path, error, attempt + 1
            )
            if error.retryable and attempt < self.max_retries:
                time.sleep(1.0 if error.kind == RATE_LIMIT else 0.6)
                attempt += 1
                continue
            raise error


_client: GnaniClient | None = None


def get_gnani_client() -> GnaniClient:
    """The shared client, built from the backend settings on first use. Raises
    GnaniError(auth) if the API key is missing, so the app still starts."""
    global _client
    if _client is None:
        from app.config import settings  # imported here to keep this module standalone

        _client = GnaniClient(
            api_key=settings.GNANI_API_KEY,
            base_url=settings.GNANI_BASE_URL,
            timeout=settings.GNANI_TIMEOUT_SECONDS,
        )
    return _client