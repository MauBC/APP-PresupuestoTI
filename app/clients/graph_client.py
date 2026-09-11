
import time
from urllib.parse import urlparse

import requests

from app.auth.msal_auth import (
    MsalAuthService,
)


class GraphClientError(
    RuntimeError
):
    pass


class GraphClient:
    BASE_URL = (
        "https://graph.microsoft.com/v1.0"
    )

    RETRY_STATUS = {
        429,
        500,
        502,
        503,
        504,
    }

    def __init__(
        self,
        *,
        auth_service=None,
        session=None,
        timeout_seconds: int = 60,
        max_retries: int = 5,
        sleep_func=time.sleep,
    ):
        if (
            isinstance(
                timeout_seconds,
                bool,
            )
            or timeout_seconds < 1
        ):
            raise ValueError(
                "timeout_seconds debe "
                "ser mayor a cero."
            )

        if (
            isinstance(
                max_retries,
                bool,
            )
            or max_retries < 1
        ):
            raise ValueError(
                "max_retries debe "
                "ser mayor a cero."
            )

        self._auth = (
            auth_service
            if auth_service is not None
            else MsalAuthService()
        )

        self._session = (
            session
            if session is not None
            else requests.Session()
        )

        self._timeout = int(
            timeout_seconds
        )

        self._max_retries = int(
            max_retries
        )

        self._sleep = (
            sleep_func
        )

    def get(
        self,
        endpoint,
        *,
        params=None,
    ):
        return self._request(
            "GET",
            endpoint,
            params=params,
        )

    def post(
        self,
        endpoint,
        *,
        json_body=None,
    ):
        return self._request(
            "POST",
            endpoint,
            json_body=json_body,
        )

    def patch(
        self,
        endpoint,
        *,
        json_body=None,
        extra_headers=None,
    ):
        return self._request(
            "PATCH",
            endpoint,
            json_body=json_body,
            extra_headers=(
                extra_headers
            ),
        )

    def delete(
        self,
        endpoint,
        *,
        extra_headers=None,
    ):
        return self._request(
            "DELETE",
            endpoint,
            extra_headers=(
                extra_headers
            ),
        )

    def get_all_pages(
        self,
        endpoint,
        *,
        params=None,
    ) -> tuple[
        dict,
        ...
    ]:
        url = endpoint
        current_params = (
            dict(params)
            if params
            else None
        )

        result = []

        while url:
            data = self.get(
                url,
                params=current_params,
            )

            if not isinstance(
                data,
                dict,
            ):
                raise GraphClientError(
                    "Respuesta inesperada "
                    "durante paginacion."
                )

            values = data.get(
                "value",
                [],
            )

            if values is None:
                values = []

            if not isinstance(
                values,
                list,
            ):
                raise GraphClientError(
                    "Graph devolvio un "
                    "campo value invalido: "
                    f"{type(values).__name__}."
                )

            result.extend(
                values
            )

            next_url = (
                data.get(
                    "@odata.nextLink"
                )
            )

            if next_url:
                self._validate_graph_url(
                    next_url
                )

            url = next_url
            current_params = None

        return tuple(
            result
        )

    def _request(
        self,
        method,
        endpoint,
        *,
        params=None,
        json_body=None,
        extra_headers=None,
    ):
        url = self._url(
            endpoint
        )

        last_error = None

        for attempt in range(
            self._max_retries
        ):
            token = (
                self._auth
                .get_access_token()
            )

            headers = {
                "Authorization":
                    f"Bearer {token}",
                "Accept":
                    "application/json",
            }

            if json_body is not None:
                headers[
                    "Content-Type"
                ] = "application/json"

            if extra_headers:
                headers.update(
                    extra_headers
                )

            try:
                response = (
                    self._session
                    .request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json_body,
                        timeout=self._timeout,
                    )
                )

            except requests.RequestException as exc:
                last_error = exc

                if (
                    attempt
                    < self._max_retries - 1
                ):
                    self._sleep(
                        min(
                            2 ** attempt,
                            30,
                        )
                    )

                    continue

                break

            if (
                response.status_code
                in self.RETRY_STATUS
                and
                attempt
                < self._max_retries - 1
            ):
                self._sleep(
                    self._retry_delay(
                        response,
                        attempt,
                    )
                )

                continue

            if not response.ok:
                body = (
                    response.text
                    or ""
                )

                body = body[
                    :1500
                ]

                raise GraphClientError(
                    "Microsoft Graph "
                    f"{method} fallo "
                    f"con HTTP "
                    f"{response.status_code}. "
                    f"{body}"
                )

            if (
                response.status_code
                == 204
                or not response.content
            ):
                return None

            content_type = (
                response.headers
                .get(
                    "Content-Type",
                    "",
                )
                .lower()
            )

            if (
                "json"
                in content_type
            ):
                try:
                    return response.json()

                except ValueError as exc:
                    raise GraphClientError(
                        "Graph devolvio JSON "
                        "invalido."
                    ) from exc

            return response.text

        raise GraphClientError(
            "No se pudo completar "
            f"{method} {url} despues "
            f"de {self._max_retries} "
            "intentos."
        ) from last_error

    @classmethod
    def _url(
        cls,
        endpoint,
    ) -> str:
        text = str(
            endpoint
        ).strip()

        if not text:
            raise GraphClientError(
                "endpoint no puede "
                "estar vacio."
            )

        if text.startswith(
            "https://"
        ):
            cls._validate_graph_url(
                text
            )

            return text

        if not text.startswith(
            "/"
        ):
            text = "/" + text

        return (
            cls.BASE_URL
            + text
        )

    @staticmethod
    def _validate_graph_url(
        url,
    ):
        parsed = urlparse(
            str(url)
        )

        if (
            parsed.scheme != "https"
            or
            parsed.hostname
            != "graph.microsoft.com"
        ):
            raise GraphClientError(
                "Graph devolvio una URL "
                "de paginacion no permitida."
            )

    @staticmethod
    def _retry_delay(
        response,
        attempt,
    ) -> float:
        retry_after_ms = (
            response.headers
            .get(
                "x-ms-retry-after-ms"
            )
        )

        if retry_after_ms:
            try:
                return min(
                    float(
                        retry_after_ms
                    )
                    / 1000.0,
                    60.0,
                )
            except ValueError:
                pass

        retry_after = (
            response.headers
            .get(
                "Retry-After"
            )
        )

        if retry_after:
            try:
                return min(
                    float(
                        retry_after
                    ),
                    60.0,
                )
            except ValueError:
                pass

        return float(
            min(
                2 ** attempt,
                30,
            )
        )
