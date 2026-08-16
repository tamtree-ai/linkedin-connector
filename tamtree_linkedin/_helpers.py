"""Helpers copied from Tamtree in-tree connectors. Do not import `tamtree_nodes`."""

from __future__ import annotations

import re
from typing import Any, Final

from tamtree_plugin_sdk import ExecutionContext, Item, NodeManifest

# `NodeConfigurationError` is not re-exported by tamtree-plugin-sdk (yet). It is
# the engine's non-retryable seam; a bare ValueError would burn the retry budget.
from tamtree_sdk import NodeConfigurationError

LINKEDIN_VERSION: Final = "202607"
POSTS_URL: Final = "https://api.linkedin.com/rest/posts"
USERINFO_URL: Final = "https://api.linkedin.com/v2/userinfo"
FEED_UPDATE_URL: Final = "https://www.linkedin.com/feed/update/{urn}"

# LinkedIn's feed renders each commentary newline as a paragraph (`<p>` with
# margin), so a markdown-style blank line (`\n\n`) shows as a double gap.
# Collapse runs after normalizing CRLF so the post matches what the author typed.
_BLANK_LINES = re.compile(r"\n{2,}")


def format_commentary(text: str) -> str:
    """Line-break normalizer for Posts API `commentary` (little text)."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return _BLANK_LINES.sub("\n", normalized).strip("\n")

POST_OUTPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean", "examples": [True]},
        "status": {"type": "integer", "examples": [201]},
        "post_urn": {"type": ["string", "null"], "examples": ["urn:li:share:123"]},
        "post_url": {
            "type": ["string", "null"],
            "examples": ["https://www.linkedin.com/feed/update/urn:li:share:123"],
        },
        "lifecycle_state": {"type": ["string", "null"], "examples": ["PUBLISHED"]},
        "error_code": {"type": ["string", "null"]},
        "error_message": {"type": ["string", "null"]},
        "body": {},
    },
    "required": [
        "ok",
        "status",
        "post_urn",
        "post_url",
        "lifecycle_state",
        "error_code",
        "error_message",
        "body",
    ],
}


def connector_manifest(**overrides: Any) -> NodeManifest:
    base: dict[str, Any] = {
        "display_name": "",
        "description": "",
        "category": "Connectors",
        "kind": "action",
        "inputs": [{"name": "main"}],
        "outputs": [{"name": "main"}],
        "params": [],
        "credentials": [],
    }
    return NodeManifest.model_validate(base | overrides)


def post_port(name: str = "main") -> dict[str, Any]:
    return {"name": name, "output_schema": POST_OUTPUT_SCHEMA}


def post_item(
    *,
    status: int,
    body: Any,
    post_urn: str | None = None,
    ok: bool | None = None,
    lifecycle_state: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> Item:
    succeeded = (200 <= status < 300) if ok is None else ok
    return Item.model_validate(
        {
            "json": {
                "ok": succeeded,
                "status": status,
                "post_urn": post_urn,
                "post_url": FEED_UPDATE_URL.format(urn=post_urn) if post_urn else None,
                "lifecycle_state": lifecycle_state if succeeded else None,
                "error_code": error_code,
                "error_message": error_message,
                "body": body if body is not None else {},
            }
        }
    )


async def bearer_token(
    ctx: ExecutionContext, credential_type: str, *, field: str = "access_token"
) -> str:
    try:
        cred = await ctx.credential(credential_type)
    except KeyError as exc:
        raise NodeConfigurationError(
            f"credential {credential_type!r} is not bound on this node"
        ) from exc
    token = cred.get(field) or cred.get("token") or cred.get("api_key")
    if not token:
        raise NodeConfigurationError(f"credential {credential_type!r} is missing {field!r}")
    return str(token)


def linkedin_headers(token: str, *, json: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Linkedin-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if json:
        headers["Content-Type"] = "application/json"
    return headers


def person_urn(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("urn:"):
        return stripped
    return f"urn:li:person:{stripped}"


def response_body(response: Any) -> Any:
    content = getattr(response, "content", None)
    if not content:
        return {}
    json_fn = getattr(response, "json", None)
    if callable(json_fn):
        try:
            return json_fn()
        except ValueError:
            pass
    text = getattr(response, "text", None)
    return text if text is not None else {}


def error_fields(body: Any) -> tuple[str | None, str | None]:
    if not isinstance(body, dict):
        text = str(body) if body else None
        return None, text
    code = body.get("code") or body.get("serviceErrorCode")
    message = body.get("message") or body.get("error_description") or body.get("error")
    if isinstance(message, dict):
        message = message.get("message")
    return (str(code) if code is not None else None, str(message) if message else None)


def raise_for_linkedin_status(status: int, body: Any, *, action: str) -> None:
    code, message = error_fields(body)
    detail = message or (repr(body) if body else "no body")
    suffix = f" ({code})" if code else ""
    if status == 429 or status >= 500:
        raise RuntimeError(f"LinkedIn {action} failed with HTTP {status}{suffix}: {detail}")
    if 400 <= status < 500:
        raise NodeConfigurationError(
            f"LinkedIn {action} failed with HTTP {status}{suffix}: {detail}"
        )
