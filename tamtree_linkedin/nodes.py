"""linkedin.create_post — personal-profile, text-only Posts API."""

from __future__ import annotations

from typing import Any, ClassVar

from tamtree_plugin_sdk import ExecutionContext, Item, ProgrammaticNode
from tamtree_sdk import NodeConfigurationError

from tamtree_linkedin._helpers import (
    POSTS_URL,
    USERINFO_URL,
    bearer_token,
    connector_manifest,
    format_commentary,
    linkedin_headers,
    person_urn,
    post_item,
    post_port,
    raise_for_linkedin_status,
    response_body,
)

_VISIBILITY = frozenset({"PUBLIC", "CONNECTIONS"})


class LinkedInCreatePostNode(ProgrammaticNode):
    name: ClassVar[str] = "linkedin.create_post"
    manifest: ClassVar = connector_manifest(
        name="linkedin.create_post",
        outputs=[post_port()],
        display_name="LinkedIn — Create post",
        description="Publish a text post to the authenticated member's LinkedIn feed.",
        icon="icons/linkedin.svg",
        credentials=[{"type": "linkedin_api", "required": True}],
        params=[
            {
                "name": "commentary",
                "label": "Post text",
                "type": "string",
                "required": True,
                "description": "Body of the post. Map from an upstream item with {{ }}.",
            },
            {
                "name": "visibility",
                "label": "Visibility",
                "type": "options",
                "default": "PUBLIC",
                "options": [
                    {"value": "PUBLIC", "label": "Anyone"},
                    {"value": "CONNECTIONS", "label": "Connections only"},
                ],
            },
            {
                "name": "author_urn",
                "label": "Author URN (optional)",
                "type": "string",
                "required": False,
                "description": (
                    "Leave blank to resolve from OpenID userinfo "
                    "(urn:li:person:{sub}). Override only if you already have the URN."
                ),
            },
        ],
    )

    async def execute(self, ctx: ExecutionContext) -> dict[str, list[Item]]:
        token = await bearer_token(ctx, "linkedin_api")
        client = ctx.http()
        headers = linkedin_headers(token, json=True)
        me_urn: str | None = None
        outputs: list[Item] = []
        for item in ctx.input_items() or [Item()]:
            commentary = ctx.param("commentary", item=item)
            if commentary is None or not str(commentary).strip():
                raise NodeConfigurationError("'commentary' is required")
            commentary = format_commentary(str(commentary))
            visibility = str(ctx.param("visibility", item=item) or "PUBLIC").upper()
            if visibility not in _VISIBILITY:
                raise NodeConfigurationError(
                    f"visibility must be PUBLIC or CONNECTIONS, got {visibility!r}"
                )
            author = ctx.param("author_urn", item=item)
            if author and str(author).strip():
                author_id = person_urn(str(author))
            else:
                if me_urn is None:
                    me_urn = await _resolve_member_urn(client, headers)
                author_id = me_urn
            response = await client.post(
                POSTS_URL,
                headers=headers,
                json={
                    "author": author_id,
                    "commentary": commentary,
                    "visibility": visibility,
                    "distribution": {
                        "feedDistribution": "MAIN_FEED",
                        "targetEntities": [],
                        "thirdPartyDistributionChannels": [],
                    },
                    "lifecycleState": "PUBLISHED",
                },
            )
            body = response_body(response)
            raise_for_linkedin_status(response.status_code, body, action="create post")
            post_urn = response.headers.get("x-restli-id") or None
            outputs.append(
                post_item(
                    status=response.status_code,
                    body=body,
                    post_urn=post_urn,
                    lifecycle_state="PUBLISHED",
                )
            )
        return {"main": outputs}


async def _resolve_member_urn(client: Any, headers: dict[str, str]) -> str:
    response = await client.get(USERINFO_URL, headers=headers)
    body = response_body(response)
    raise_for_linkedin_status(response.status_code, body, action="userinfo")
    if not isinstance(body, dict) or not body.get("sub"):
        raise NodeConfigurationError("LinkedIn userinfo did not return a member id (sub)")
    return person_urn(str(body["sub"]))
