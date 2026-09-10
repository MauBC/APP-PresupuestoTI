
import pytest

from app.auth.msal_auth import (
    MicrosoftAuthError,
    MsalAuthService,
)


pytestmark = pytest.mark.unit


class FakeApp:
    def __init__(
        self,
        result,
    ):
        self.result = result
        self.scopes = None

    def acquire_token_for_client(
        self,
        scopes,
    ):
        self.scopes = scopes
        return self.result


def test_auth_returns_token():
    app = FakeApp(
        {
            "access_token":
                "token-test"
        }
    )

    service = MsalAuthService(
        tenant_id="tenant",
        client_id="client",
        client_secret="secret",
        scope="scope/.default",
        app_factory=(
            lambda **kwargs:
                app
        ),
    )

    assert (
        service.get_access_token()
        == "token-test"
    )

    assert app.scopes == [
        "scope/.default"
    ]


def test_auth_rejects_empty_config():
    with pytest.raises(
        MicrosoftAuthError,
        match="MS_TENANT_ID",
    ):
        MsalAuthService(
            tenant_id=" ",
            client_id="client",
            client_secret="secret",
            scope="scope",
        )


def test_auth_failure_is_explicit():
    app = FakeApp(
        {
            "error":
                "invalid_client",
            "error_description":
                "Synthetic failure",
        }
    )

    service = MsalAuthService(
        tenant_id="tenant",
        client_id="client",
        client_secret="secret",
        scope="scope",
        app_factory=(
            lambda **kwargs:
                app
        ),
    )

    with pytest.raises(
        MicrosoftAuthError,
        match="invalid_client",
    ):
        service.get_access_token()
