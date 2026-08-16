"""LinkedIn OAuth credential type contributed as data (D-G6)."""

from tamtree_plugin_sdk import CredentialFieldSpec, CredentialTypeSpec

AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "openid profile w_member_social"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

# `CredentialFieldSpec` currently has `placeholder` only — no `default`. Until
# Tamtree applies field defaults on create, paste these URLs/scopes from the
# placeholders (or bind the built-in `oauth2` type). Named `linkedin_api` OAuth
# also needs Tamtree to key the connect flow on `auth_kind`, not type name
# `"oauth2"`. See README.
LINKEDIN_API = CredentialTypeSpec(
    type="linkedin_api",
    display_name="LinkedIn",
    description="OAuth2 access for personal LinkedIn posting (Share on LinkedIn).",
    auth_kind="oauth2",
    fields=[
        CredentialFieldSpec(name="client_id", label="Client ID", secret=False),
        CredentialFieldSpec(name="client_secret", label="Client secret", secret=True),
        CredentialFieldSpec(
            name="authorize_url",
            label="Authorize URL",
            secret=False,
            placeholder=AUTHORIZE_URL,
        ),
        CredentialFieldSpec(
            name="token_url",
            label="Token URL",
            secret=False,
            placeholder=TOKEN_URL,
        ),
        CredentialFieldSpec(
            name="scopes",
            label="Scopes",
            secret=False,
            required=False,
            placeholder=SCOPES,
        ),
        CredentialFieldSpec(
            name="test_url",
            label="Userinfo URL (optional)",
            secret=False,
            required=False,
            placeholder=USERINFO_URL,
        ),
    ],
    test_url_field="test_url",
)
