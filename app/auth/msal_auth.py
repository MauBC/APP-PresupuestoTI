
import msal

from app.config.settings import (
    settings,
)


class MicrosoftAuthError(
    RuntimeError
):
    pass


class MsalAuthService:
    def __init__(
        self,
        *,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        scope: str | None = None,
        app_factory=None,
    ):
        self._tenant_id = (
            self._required(
                (
                    settings.MS_TENANT_ID
                    if tenant_id is None
                    else tenant_id
                ),
                "MS_TENANT_ID",
            )
        )

        self._client_id = (
            self._required(
                (
                    settings.MS_CLIENT_ID
                    if client_id is None
                    else client_id
                ),
                "MS_CLIENT_ID",
            )
        )

        self._client_secret = (
            self._required(
                (
                    settings.MS_CLIENT_SECRET
                    if client_secret is None
                    else client_secret
                ),
                "MS_CLIENT_SECRET",
            )
        )

        self._scope = (
            self._required(
                (
                    settings.MS_GRAPH_SCOPE
                    if scope is None
                    else scope
                ),
                "MS_GRAPH_SCOPE",
            )
        )

        self._authority = (
            "https://login.microsoftonline.com/"
            f"{self._tenant_id}"
        )

        factory = (
            msal.ConfidentialClientApplication
            if app_factory is None
            else app_factory
        )

        self._app = factory(
            client_id=self._client_id,
            client_credential=(
                self._client_secret
            ),
            authority=self._authority,
        )

    @property
    def authority(
        self,
    ) -> str:
        return self._authority

    @property
    def scope(
        self,
    ) -> str:
        return self._scope

    def get_access_token(
        self,
    ) -> str:
        result = (
            self._app
            .acquire_token_for_client(
                scopes=[
                    self._scope
                ]
            )
        )

        token = str(
            result.get(
                "access_token",
                "",
            )
            or ""
        ).strip()

        if token:
            return token

        error = str(
            result.get(
                "error",
                "unknown_error",
            )
        )

        description = str(
            result.get(
                "error_description",
                "No se pudo obtener "
                "el token.",
            )
        )

        raise MicrosoftAuthError(
            "Error autenticando con "
            f"Microsoft: {error} - "
            f"{description}"
        )

    @staticmethod
    def _required(
        value,
        name,
    ) -> str:
        text = str(
            value
            if value is not None
            else ""
        ).strip()

        if not text:
            raise MicrosoftAuthError(
                f"{name} no esta configurado."
            )

        return text
