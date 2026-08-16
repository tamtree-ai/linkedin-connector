"""Focused tests for linkedin.create_post (mocked HTTP, no live LinkedIn)."""

import json

import httpx
import pytest
from tamtree_plugin_sdk import Item
from tamtree_plugin_sdk.testing import NodeTestKit
from tamtree_sdk import NodeConfigurationError

from tamtree_linkedin.nodes import LinkedInCreatePostNode

_TOKEN = "tok-test"
_PERSON = "urn:li:person:abc"
_SHARE = "urn:li:share:6844785523593134080"


def _kit(**params: object) -> NodeTestKit:
    defaults = {"commentary": "Hello from Tamtree"}
    defaults.update(params)
    return (
        NodeTestKit(LinkedInCreatePostNode())
        .params(**defaults)
        .credentials({"linkedin_api": {"access_token": _TOKEN}})
    )


async def test_create_post_resolves_member_and_reads_restli_id() -> None:
    kit = _kit().responses(
        [
            httpx.Response(200, json={"sub": "abc"}),
            httpx.Response(201, headers={"x-restli-id": _SHARE}),
        ]
    )
    outputs = await kit.run()
    kit.assert_request(
        0,
        method="GET",
        url="https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {_TOKEN}", "Linkedin-Version": "202607"},
    )
    kit.assert_request(
        1,
        method="POST",
        url="https://api.linkedin.com/rest/posts",
        headers={
            "Authorization": f"Bearer {_TOKEN}",
            "Linkedin-Version": "202607",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json_body={
            "author": _PERSON,
            "commentary": "Hello from Tamtree",
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
        },
    )
    item = outputs["main"][0].json_
    assert item["ok"] is True
    assert item["status"] == 201
    assert item["post_urn"] == _SHARE
    assert item["post_url"] == f"https://www.linkedin.com/feed/update/{_SHARE}"
    assert item["lifecycle_state"] == "PUBLISHED"
    assert item["error_code"] is None
    assert item["error_message"] is None


async def test_create_post_skips_userinfo_when_author_urn_set() -> None:
    kit = _kit(author_urn="abc").responses([httpx.Response(201, headers={"x-restli-id": _SHARE})])
    outputs = await kit.run()
    assert len(kit.requests) == 1
    kit.assert_request(0, method="POST", url="https://api.linkedin.com/rest/posts")
    assert outputs["main"][0].json_["post_urn"] == _SHARE


async def test_create_post_uses_full_author_urn() -> None:
    kit = _kit(author_urn=_PERSON).responses([httpx.Response(201, headers={"x-restli-id": _SHARE})])
    await kit.run()
    assert json.loads(kit.requests[0].content)["author"] == _PERSON


async def test_create_post_per_item_commentary() -> None:
    kit = (
        _kit()
        .inputs(
            "main",
            [
                Item.model_validate({"json": {"text": "first"}}),
                Item.model_validate({"json": {"text": "second"}}),
            ],
        )
        .params(commentary=lambda item: item.json_["text"] if item else "")
        .responses(
            [
                httpx.Response(200, json={"sub": "abc"}),
                httpx.Response(201, headers={"x-restli-id": "urn:li:share:1"}),
                httpx.Response(201, headers={"x-restli-id": "urn:li:share:2"}),
            ]
        )
    )
    outputs = await kit.run()
    assert [o.json_["post_urn"] for o in outputs["main"]] == [
        "urn:li:share:1",
        "urn:li:share:2",
    ]
    assert json.loads(kit.requests[1].content)["commentary"] == "first"
    assert json.loads(kit.requests[2].content)["commentary"] == "second"
    # userinfo is resolved once for the batch
    assert kit.requests[0].method == "GET"
    assert len(kit.requests) == 3


async def test_create_post_connections_visibility() -> None:
    kit = _kit(visibility="CONNECTIONS", author_urn=_PERSON).responses(
        [httpx.Response(201, headers={"x-restli-id": _SHARE})]
    )
    await kit.run()
    assert json.loads(kit.requests[0].content)["visibility"] == "CONNECTIONS"


async def test_missing_token_is_configuration_error() -> None:
    kit = (
        NodeTestKit(LinkedInCreatePostNode())
        .params(commentary="hi")
        .credentials({"linkedin_api": {}})
        .responses([])
    )
    with pytest.raises(NodeConfigurationError, match="missing 'access_token'"):
        await kit.run()


async def test_unbound_credential_is_configuration_error() -> None:
    kit = NodeTestKit(LinkedInCreatePostNode()).params(commentary="hi").responses([])
    with pytest.raises(NodeConfigurationError, match="is not bound"):
        await kit.run()


async def test_blank_commentary_is_configuration_error() -> None:
    kit = _kit(commentary="  ", author_urn=_PERSON).responses([])
    with pytest.raises(NodeConfigurationError, match="commentary"):
        await kit.run()


async def test_forbidden_is_configuration_error() -> None:
    kit = _kit(author_urn=_PERSON).responses(
        [
            httpx.Response(
                403,
                json={"code": "ACCESS_DENIED", "message": "Not enough permissions"},
            )
        ]
    )
    with pytest.raises(NodeConfigurationError, match="ACCESS_DENIED"):
        await kit.run()


async def test_userinfo_unauthorized_is_configuration_error() -> None:
    kit = _kit().responses([httpx.Response(401, json={"message": "Expired"})])
    with pytest.raises(NodeConfigurationError, match="HTTP 401"):
        await kit.run()


async def test_rate_limit_is_retryable() -> None:
    kit = _kit(author_urn=_PERSON).responses(
        [httpx.Response(429, json={"message": "too many requests"})]
    )
    with pytest.raises(RuntimeError, match="HTTP 429"):
        await kit.run()


async def test_server_error_is_retryable() -> None:
    kit = _kit(author_urn=_PERSON).responses([httpx.Response(503, json={"message": "unavailable"})])
    with pytest.raises(RuntimeError, match="HTTP 503"):
        await kit.run()
