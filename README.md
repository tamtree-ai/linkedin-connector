# LinkedIn connector for Tamtree

Publish a **text post** to the authenticated member’s LinkedIn feed from a Tamtree pipeline, and get a **structured status** back — post URN, URL, HTTP status — not a silent 201.

This is a **community plugin** in its own git repo. Tamtree never vendors the source. At boot it discovers two Python entry points, the same way it loads Slack and Gmail from `tamtree-nodes`.

| | |
|---|---|
| **Palette** | LinkedIn — Create post |
| **Node type** | `linkedin.create_post` |
| **Credential** | LinkedIn (`linkedin_api`, OAuth2) |
| **Plugin / allowlist** | `linkedin-connector` |
| **Wheel** | `tamtree-linkedin-connector` |
| **Contracts** | `tamtree-plugin-sdk` `^1.0` (tested against Tamtree `CONTRACTS_VERSION` 1.27.0) |

v1 is **personal profile, text only** (`openid profile w_member_social` / Share on LinkedIn). Images, video, documents, and company pages are later — company posting needs LinkedIn’s Community Management product and partner review.

---

## Why a code plugin

LinkedIn’s create-post success is **HTTP 201, empty body, post id in the `x-restli-id` header**. Tamtree’s declarative HTTP executor (`HttpOperationSpec`) reads the **body only** and drops headers. An empty JSON body becomes zero output items — no `ok`, no URN, no URL.

This node is a thin `ctx.http()` wrapper that:

1. Resolves `urn:li:person:{sub}` from OpenID `GET /v2/userinfo` (skipped if you set **Author URN**).
2. `POST https://api.linkedin.com/rest/posts` with `Linkedin-Version: 202607`.
3. Maps the Rest.li header onto a **declared** output schema so downstream nodes can map fields before a run.

```mermaid
sequenceDiagram
  participant Flow as Pipeline
  participant Node as linkedin.create_post
  participant LI as LinkedIn API

  Flow->>Node: commentary (+ optional visibility / author URN)
  Node->>LI: GET /v2/userinfo
  LI-->>Node: sub
  Node->>LI: POST /rest/posts
  LI-->>Node: 201 + x-restli-id
  Node-->>Flow: ok, status, post_urn, post_url
```

---

## Node

**Credentials:** `linkedin_api` (required).

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `commentary` | string | yes | — | Post body. Map from an upstream item with `{{ }}`. |
| `visibility` | options | no | `PUBLIC` | `PUBLIC` or `CONNECTIONS`. |
| `author_urn` | string | no | *(userinfo)* | `urn:li:person:…` or a bare member id. Blank → OpenID `sub`. |

One output item per input item (or a single item if the port is empty). Userinfo is resolved **once per execute** and reused across the batch.

### Output (`main`)

```json
{
  "ok": true,
  "status": 201,
  "post_urn": "urn:li:share:6844785523593134080",
  "post_url": "https://www.linkedin.com/feed/update/urn:li:share:6844785523593134080",
  "lifecycle_state": "PUBLISHED",
  "error_code": null,
  "error_message": null,
  "body": {}
}
```

| HTTP | What the node does |
|---|---|
| `2xx` | `ok: true`, URN from `x-restli-id` |
| `4xx` except `429` | `NodeConfigurationError` — non-retryable (reconnect, scopes, bad text) |
| `429` / `5xx` | plain `RuntimeError` — engine retries |

The access token is never written onto the item.

**Rate limit:** Share on LinkedIn is on the order of **150 requests / member / day**. Budget userinfo + create as two calls when Author URN is blank.

---

## LinkedIn developer app

1. Create an app at the [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps).
2. Add products:
   - **Sign In with LinkedIn using OpenID Connect** — `openid profile`
   - **Share on LinkedIn** — `w_member_social` (personal posting; no partner wait)
3. Auth tab → **Authorized redirect URLs** — exact match, HTTPS, no wildcards:

| Tamtree | Register this one URL |
|---|---|
| After the [named-OAuth platform PR](#oauth-needs-a-tamtree-platform-pr) | `https://<your-tamtree-host>/api/oauth/callback` |
| Today (callback still includes the credential UUID) | `https://<your-tamtree-host>/api/oauth/callback/<credential-id>` — only after the credential row exists |

LinkedIn rejects a mismatch. There is no wildcard, and a new credential is a new UUID, which is why the stable callback is required for a usable connect flow.

Client ID and Client secret go into the Tamtree credential. Authorize / token URLs and scopes:

| Field | Value |
|---|---|
| Authorize | `https://www.linkedin.com/oauth/v2/authorization` |
| Token | `https://www.linkedin.com/oauth/v2/accessToken` |
| Scopes | `openid profile w_member_social` |
| Userinfo (optional probe) | `https://api.linkedin.com/v2/userinfo` |

Access tokens last **~60 days**. Tamtree refreshes when `refresh_token` and `token_url` are present — once OAuth is keyed on `auth_kind` (see below).

---

## Install

### Local Tamtree checkout

```sh
cd ~/sites/tamtree
uv pip install -e ~/sites/tamtree-plugins/linkedin-connector
# restart API + engine workers
```

Live-dev (dev-only — a production boot **refuses** this env var):

```sh
mkdir -p ~/tamtree-plugins
ln -s ~/sites/tamtree-plugins/linkedin-connector ~/tamtree-plugins/linkedin-connector

# terminal 1
TAMTREE_DEV_PLUGINS_DIR=$HOME/tamtree-plugins make dev

# terminal 2
TAMTREE_DEV_PLUGINS_DIR=$HOME/tamtree-plugins make worker
```

Allowlist — optional on a laptop; **required** if the variable is set at all. An allowlist that omits this plugin **refuses the entire boot**.

```sh
TAMTREE_PLUGINS_ALLOWED=linkedin-connector
```

Empty allowlist = every installed plugin loads.

### Production image

This repo ships a `Dockerfile` that layers the wheel onto the official Tamtree image:

```dockerfile
ARG TAMTREE_VERSION=0.1.0
FROM ghcr.io/tamtree/tamtree:${TAMTREE_VERSION}
# … uv pip install this directory
```

```sh
docker build --build-arg TAMTREE_VERSION=0.1.0 -t tamtree:linkedin .
```

Pin `tamtree-linkedin-connector==0.1.0` in the instance plugin-set, bake, recycle workers (`make plugins-recycle` / Helm roll). Writing `POST /api/admin/plugin-set` installs **nothing by itself** — code arrives only in the next image.

---

## Connect and run a flow

1. **Credentials** → add **LinkedIn**. Client ID + Client secret (URLs/scopes are placeholders until Tamtree grows field defaults).
2. **Save & connect** — completes only after the platform PR below.
3. Canvas: **LinkedIn — Create post**. Bind the credential. Map upstream text into **Post text**.
4. Run. Downstream: branch on `ok` / `status`, or pass `post_url` to a notification node.

### Enable / disable

| Layer | What it does | Restart? |
|---|---|---|
| **Extensions** page switch | Per-workspace. Palette hides the node; in-flight steps fail non-retryably. Code stays loaded. | No |
| `TAMTREE_PLUGINS_ALLOWED` | Instance-wide boot allowlist. Omit + recycle to hide without rebuilding. | Recycle workers |
| Drop the wheel | Real uninstall. | Rebuild image |

Re-enable is the same switch. Disable does **not** `sys.modules.pop`.

---

## OAuth: needs a Tamtree platform PR

The node binds type **`linkedin_api`** with `auth_kind="oauth2"`. Tamtree’s OAuth machinery is still keyed on the **type name** `"oauth2"`, not `auth_kind`.

On unpatched Tamtree:

| Surface | What happens |
|---|---|
| Create form | **Save & connect** (frontend reads `auth_kind`) |
| After save | **No redirect** (`CredentialsPage` only redirects when `created.type === 'oauth2'`) |
| `GET /api/credentials/{id}/authorize` | **422** (`row.type != "oauth2"`) |
| Token refresh | **Skipped** (`credentials.py` same check) |
| Connected / Expired | **Never shown** |

The same gap already affects built-in **`google_api`** (Gmail, Sheets). Fixing it is a platform change, not LinkedIn-specific.

This node **cannot** fall back to the generic OAuth2 type: `ctx.credential("linkedin_api")` only sees a credential bound as LinkedIn.

Until that PR lands you can still **install**, **see the node**, and **run the unit tests**. Live posting waits on Tamtree.

Requirement (implementation plan): `changes/2026-08-16-connector-pool/01-oauth-named-types.md` in the Tamtree planning repo — three additive changes:

1. Key OAuth on `auth_kind` via `merged_credential_types(registry)` (unblocks `linkedin_api` **and** `google_api`).
2. Stable callback `{public_url}/api/oauth/callback` (credential id in stored state / lookup; keep the old path as an alias).
3. Optional `CredentialFieldSpec.default` so LinkedIn URLs and scopes auto-fill.

After (1)+(2): register **one** redirect URL on the LinkedIn app. After (3): the plugin will pin those defaults in a follow-up release.

---

## Develop

This `pyproject.toml` path-depends on a Tamtree checkout at `../../tamtree` (`tamtree-plugin-sdk` + `tamtree-sdk`). Without that tree:

```sh
uv add 'tamtree-plugin-sdk[testing] @ git+https://github.com/tamtree/tamtree@main#subdirectory=packages/plugin-sdk'
```

```sh
uv sync --extra testing --extra dev
uv run pytest          # 18 tests, no network, no LinkedIn
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Imports: `tamtree_plugin_sdk` only, except `NodeConfigurationError` (not yet re-exported by the facade — `from tamtree_sdk import NodeConfigurationError`). **Never** `tamtree_server` or `tamtree_nodes`.

Manual smoke (after the platform PR): LinkedIn app → connect → one-node flow with a throwaway post.

---

## Out of scope (v1)

- Images / video / documents (Images API register-upload, then Posts API `content.media`)
- Company pages (`w_organization_social`, organization URN, partner approval)
- Polling trigger (“new mentions”) — `r_member_social` is restricted
- In-tree palette brand icon (`BRAND_ICON_TYPE`) — studio falls back to the Connectors glyph
- Tamtree Cloud in-process install (SEC-G1: code plugins are image-bake only)

---

## License

Apache-2.0
