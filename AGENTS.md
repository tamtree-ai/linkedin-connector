# AGENTS.md — linkedin-connector

A [Tamtree](https://www.tamtree.io) community plugin: one node, `linkedin.create_post`, that
publishes a text post to the authenticated member's LinkedIn profile through the Posts API and
returns the post URN, URL and HTTP status. [README.md](README.md) has the full design.

## Layout

```
tamtree_linkedin/nodes.py               the node: userinfo lookup, POST /rest/posts, output mapping
tamtree_linkedin/credentials.py         the `linkedin_api` OAuth2 credential type
tamtree_linkedin/tamtree-plugin.toml    plugin manifest (pins sdk = "^1.28")
tests/                                  contract, registration and create-post tests (no network)
```

## Commands

```sh
uv sync --extra testing --extra dev
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

The tests need a Tamtree checkout at `../../tamtree` (see README "Develop").

## Rules

- Import from `tamtree_plugin_sdk` only. The one exception is `NodeConfigurationError`, from
  `tamtree_sdk`. Never import `tamtree_server` or `tamtree_nodes`.
- Tests never call LinkedIn. They queue canned `httpx.Response`s on the SDK test kit
  (`.responses([...])`), as in `tests/test_create_post.py`.
- Git: no `Co-Authored-By` or "Generated with" footers.
