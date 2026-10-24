"""CLI browser authorization requests and credential responses."""

from datetime import datetime
from typing import Literal
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.schemas.auth import UserResponse

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
CALLBACK_RULE = "Use an HTTP loopback callback with an explicit port and no code or state parameter"


def validate_loopback_redirect(value: str) -> str:
    """Accept an HTTP loopback callback with an explicit port and no code or state parameter."""
    if "\\" in value or "#" in value or any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError(CALLBACK_RULE)
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError(CALLBACK_RULE) from exc
    names = {name.lower() for name, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if (
        parsed.scheme != "http"
        or parsed.hostname not in LOOPBACK_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port is None
        or not 1 <= port <= 65535
        or names & {"code", "state"}
    ):
        raise ValueError(CALLBACK_RULE)
    return value


class CliStartRequest(BaseModel):
    """The requesting client's PKCE challenge and callback or manual mode."""

    model_config = ConfigDict(extra="forbid")

    client_name: str = Field(min_length=1, max_length=100)
    mode: Literal["callback", "code"]
    redirect_uri: str | None = Field(default=None, max_length=500)
    code_challenge: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    state: str = Field(min_length=1, max_length=128)

    @field_validator("client_name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        """Trim the displayed client name and reject an empty name."""
        value = value.strip()
        if not value:
            raise ValueError("A client name is required")
        return value

    @model_validator(mode="after")
    def validate_mode(self):
        """Require a loopback target for callback requests and none for manual-code requests."""
        if self.mode == "callback":
            if self.redirect_uri is None:
                raise ValueError("A callback URL is required")
            validate_loopback_redirect(self.redirect_uri)
        elif self.redirect_uri is not None:
            raise ValueError("Manual-code requests take no callback URL")
        return self


class CliExpiryResponse(BaseModel):
    """A response with an explicitly UTC authorization deadline."""

    expires_at: datetime

    @field_serializer("expires_at")
    def serialize_expiry(self, dt: datetime) -> str:
        """Serialize the stored UTC deadline with the UTC marker."""
        return f"{dt.isoformat()}Z"


class CliStartResponse(CliExpiryResponse):
    """The browser approval destination and authorization lifetime."""

    session_id: UUID
    authorize_url: str


class CliSessionResponse(CliExpiryResponse):
    """Consent metadata, the request time and the request code, without authorization secrets."""

    session_id: UUID
    client_name: str
    mode: Literal["callback", "code"]
    redirect_uri: str | None
    consumed: bool
    created_at: datetime
    request_code: str

    @field_serializer("created_at")
    def serialize_created(self, dt: datetime) -> str:
        """Serialize the stored UTC request time with the UTC marker."""
        return f"{dt.isoformat()}Z"


class CliApproveRequest(BaseModel):
    """The browser's explicit approval of one pending request."""

    model_config = ConfigDict(extra="forbid")
    session_id: UUID


class CliCallbackApproval(BaseModel):
    """The registered loopback callback carrying the one-time code and the state."""

    redirect_to: str


class CliDenyRequest(CliApproveRequest):
    """The browser's explicit denial of one pending request."""


class CliCallbackDenial(BaseModel):
    """The registered loopback callback carrying error=access_denied and the state."""

    redirect_to: str


class CliCodeDenial(BaseModel):
    """The empty answer to a denied manual-code request."""

    model_config = ConfigDict(extra="forbid")


class CliCodeApproval(CliExpiryResponse):
    """The one-time code for a client without a loopback listener."""

    exchange_code: str


class CliExchangeRequest(CliApproveRequest):
    """A one-time code and the original client's PKCE verifier."""

    code: str = Field(min_length=1, max_length=256)
    code_verifier: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$")


class CliRefreshRequest(BaseModel):
    """A rotating refresh credential supplied outside browser cookies."""

    model_config = ConfigDict(extra="forbid")
    refresh_token: str = Field(min_length=1, max_length=256)


class CliTokenResponse(BaseModel):
    """User-scoped access and refresh credentials with Bloom's existing account view."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse
