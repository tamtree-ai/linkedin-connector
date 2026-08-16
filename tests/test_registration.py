"""Boot-time PluginRegistry.discover() — the refusal paths MinIO also pinned."""

from importlib.metadata import EntryPoint
from importlib.resources import files

import pytest
from tamtree_plugin_sdk import GROUP_CREDENTIAL_TYPES, GROUP_NODES, PluginRegistry

# `tamtree_plugin_sdk` re-exports `PluginManifestError` but not
# `PluginRefusedError`, so the boot-refusal test has to reach into the kernel.
# Test-only; nothing in `tamtree_linkedin` imports `tamtree_sdk`.
from tamtree_sdk import PluginRefusedError

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


def test_fixed_vendor_fields_carry_defaults() -> None:
    """Contracts 1.28: the server fills these in on create, so nobody retypes them.

    The probe URL is deliberately *not* defaulted — it is opt-in, and a default
    would start a userinfo call on every credential.
    """
    by_name = {field.name: field for field in LINKEDIN_API.fields}
    assert by_name["authorize_url"].default == AUTHORIZE_URL
    assert by_name["token_url"].default == TOKEN_URL
    assert by_name["scopes"].default == SCOPES
    assert by_name["test_url"].default is None
    assert by_name["client_id"].default is None
    assert by_name["client_secret"].default is None


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
    assert plugin.manifest.contracts.sdk == "^1.28"


def test_pre_1_28_instance_refuses_the_plugin_at_boot() -> None:
    """The floor is a boot refusal, not a degraded connect flow (§20.3).

    Below 1.28 OAuth is keyed on the type name `"oauth2"`, so `linkedin_api`
    could never connect, and `CredentialFieldSpec.default` does not exist.
    Installing anyway would show a credential form that cannot be completed.
    """
    registry = PluginRegistry(contracts_version="1.27.0")
    with pytest.raises(PluginRefusedError, match="refused at boot"):
        registry.discover(
            lambda: [
                EntryPoint(
                    name="linkedin_api",
                    value="tamtree_linkedin:LINKEDIN_API",
                    group=GROUP_CREDENTIAL_TYPES,
                )
            ]
        )
