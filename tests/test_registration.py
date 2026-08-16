"""Boot-time PluginRegistry.discover() — the refusal paths MinIO also pinned."""

from importlib.metadata import EntryPoint
from importlib.resources import files

from tamtree_plugin_sdk import GROUP_CREDENTIAL_TYPES, GROUP_NODES, PluginRegistry

from tamtree_linkedin import LINKEDIN_API, LinkedInCreatePostNode
from tamtree_linkedin.credentials import AUTHORIZE_URL, SCOPES, TOKEN_URL


def test_credential_type_shape() -> None:
    assert LINKEDIN_API.type == "linkedin_api"
    assert LINKEDIN_API.auth_kind == "oauth2"
    names = [field.name for field in LINKEDIN_API.fields]
    assert names == [
        "client_id",
        "client_secret",
        "authorize_url",
        "token_url",
        "scopes",
        "test_url",
    ]
    by_name = {field.name: field for field in LINKEDIN_API.fields}
    assert by_name["authorize_url"].placeholder == AUTHORIZE_URL
    assert by_name["token_url"].placeholder == TOKEN_URL
    assert by_name["scopes"].placeholder == SCOPES
    assert by_name["client_secret"].secret is True


def test_node_name_matches_manifest() -> None:
    node = LinkedInCreatePostNode()
    assert node.name == node.manifest.name == "linkedin.create_post"


def test_node_ships_thesvg_linkedin_mark() -> None:
    """Package-relative SVG for the plugin-icon path (`manifest.icon`).

    Vendored with `npx @thesvg/cli add linkedin` — the same registry Tamtree
    uses for in-tree brand marks. Square viewBox, well under the 20 KB cap.
    """
    node = LinkedInCreatePostNode()
    assert node.manifest.icon == "icons/linkedin.svg"
    svg = (files("tamtree_linkedin") / "icons/linkedin.svg").read_bytes()
    assert len(svg) < 20_000
    text = svg.decode()
    assert 'viewBox="0 0 256 256"' in text
    assert 'fill="#0A66C2"' in text


def test_plugin_discovers_node_and_credential_type() -> None:
    registry = PluginRegistry()
    registry.discover(
        lambda: [
            EntryPoint(
                name="create_post",
                value="tamtree_linkedin:NODES",
                group=GROUP_NODES,
            ),
            EntryPoint(
                name="linkedin_api",
                value="tamtree_linkedin:LINKEDIN_API",
                group=GROUP_CREDENTIAL_TYPES,
            ),
        ]
    )
    assert "linkedin.create_post" in registry.nodes()
    assert registry.node_plugins()["linkedin.create_post"] == "linkedin-connector"
    spec = registry.credential_types()["linkedin_api"]
    assert spec.auth_kind == "oauth2"
    assert registry.credential_type_plugins()["linkedin_api"] == "linkedin-connector"
    plugin = registry.plugins()["linkedin-connector"]
    assert "node" in plugin.manifest.kinds
    assert "credential_type" in plugin.manifest.kinds
    assert "network" in plugin.manifest.capabilities.permissions
    assert "api.linkedin.com" in plugin.manifest.capabilities.egress_allowlist
