"""NodeContract conformance for linkedin.create_post."""

import httpx
from tamtree_plugin_sdk.testing import FakeContext, NodeContract, NodeTestKit

from tamtree_linkedin.nodes import LinkedInCreatePostNode


class TestLinkedInCreatePostContract(NodeContract):
    def make_node(self) -> LinkedInCreatePostNode:
        return LinkedInCreatePostNode()

    def make_context(self) -> FakeContext:
        kit = (
            NodeTestKit(LinkedInCreatePostNode())
            .params(commentary="Hello from Tamtree")
            .credentials({"linkedin_api": {"access_token": "tok"}})
            .responses(
                [
                    httpx.Response(200, json={"sub": "abc"}),
                    httpx.Response(201, headers={"x-restli-id": "urn:li:share:1"}),
                ]
            )
        )
        return kit.context()
