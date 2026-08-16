"""LinkedIn OAuth credential type contributed as data (D-G6)."""

from tamtree_plugin_sdk import CredentialFieldSpec, CredentialTypeSpec

AUTHORIZE_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "openid profile w_member_social"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

# LinkedIn's endpoints and scope string are the same for every app, so they are
# `default=` (contracts >= 1.28): the server fills them in on create when the
# author left the field blank — never on update, never over a supplied value.
# `placeholder` is kept alongside because it is what the *form* shows; the
# frontend does not read `default` yet, the server applies it.
#
# `test_url` is deliberately not defaulted: it is an opt-in probe, and filling
# it in would start a userinfo call on every credential nobody asked for.
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
            default=AUTHORIZE_URL,
        ),
        CredentialFieldSpec(
            name="token_url",
            label="Token URL",
            secret=False,
            placeholder=TOKEN_URL,
            default=TOKEN_URL,
        ),
        CredentialFieldSpec(
            name="scopes",
            label="Scopes",
            secret=False,
            required=False,
            placeholder=SCOPES,
            default=SCOPES,
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
