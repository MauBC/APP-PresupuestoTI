
from app.clients.graph_client import (
    GraphClient,
)
from app.config.settings import (
    settings,
)


class SharePointClientError(
    RuntimeError
):
    pass


class SharePointClient:
    def __init__(
        self,
        *,
        graph_client=None,
        hostname: str | None = None,
        site_path: str | None = None,
    ):
        self._graph = (
            graph_client
            if graph_client is not None
            else GraphClient()
        )

        self._hostname = (
            self._required(
                (
                    settings
                    .SHAREPOINT_HOSTNAME
                    if hostname is None
                    else hostname
                ),
                "SHAREPOINT_HOSTNAME",
            )
        )

        self._site_path = (
            self._normalize_site_path(
                (
                    settings
                    .SHAREPOINT_SITE_PATH
                    if site_path is None
                    else site_path
                )
            )
        )

        self._site = None
        self._lists = None
        self._list_cache = {}

    def get_site(
        self,
    ) -> dict:
        if self._site is None:
            endpoint = (
                "/sites/"
                f"{self._hostname}:"
                f"{self._site_path}"
            )

            data = (
                self._graph
                .get(
                    endpoint
                )
            )

            if not isinstance(
                data,
                dict,
            ):
                raise (
                    SharePointClientError(
                        "Respuesta de sitio "
                        "SharePoint invalida."
                    )
                )

            site_id = str(
                data.get(
                    "id",
                    "",
                )
            ).strip()

            if not site_id:
                raise (
                    SharePointClientError(
                        "SharePoint no devolvio "
                        "site_id."
                    )
                )

            self._site = data

        return dict(
            self._site
        )

    def get_site_id(
        self,
    ) -> str:
        return str(
            self.get_site()[
                "id"
            ]
        )

    def get_lists(
        self,
        *,
        refresh=False,
    ):
        if (
            self._lists is None
            or refresh
        ):
            site_id = (
                self.get_site_id()
            )

            self._lists = (
                self._graph
                .get_all_pages(
                    f"/sites/{site_id}/lists"
                )
            )

            if refresh:
                self._list_cache.clear()

        return tuple(
            self._lists
        )

    def get_list(
        self,
        list_name,
    ) -> dict:
        key = (
            self._required(
                list_name,
                "list_name",
            )
            .casefold()
        )

        cached = (
            self._list_cache
            .get(
                key
            )
        )

        if cached is not None:
            return dict(
                cached
            )

        for item in (
            self.get_lists()
        ):
            display_name = str(
                item.get(
                    "displayName",
                    "",
                )
                or ""
            ).strip()

            internal_name = str(
                item.get(
                    "name",
                    "",
                )
                or ""
            ).strip()

            if key in {
                display_name.casefold(),
                internal_name.casefold(),
            }:
                self._list_cache[
                    key
                ] = item

                return dict(
                    item
                )

        raise SharePointClientError(
            "No se encontro la lista "
            f"'{list_name}'."
        )

    def get_list_id(
        self,
        list_name,
    ) -> str:
        list_id = str(
            self.get_list(
                list_name
            ).get(
                "id",
                "",
            )
        ).strip()

        if not list_id:
            raise SharePointClientError(
                "SharePoint no devolvio "
                "list_id."
            )

        return list_id

    def get_columns(
        self,
        list_name,
    ):
        site_id = (
            self.get_site_id()
        )

        list_id = (
            self.get_list_id(
                list_name
            )
        )

        return (
            self._graph
            .get_all_pages(
                "/sites/"
                f"{site_id}/lists/"
                f"{list_id}/columns"
            )
        )

    def get_items(
        self,
        list_name,
    ):
        site_id = (
            self.get_site_id()
        )

        list_id = (
            self.get_list_id(
                list_name
            )
        )

        return (
            self._graph
            .get_all_pages(
                "/sites/"
                f"{site_id}/lists/"
                f"{list_id}/items",
                params={
                    "$expand":
                        "fields"
                },
            )
        )

    def create_item(
        self,
        list_name,
        fields,
    ):
        site_id = (
            self.get_site_id()
        )

        list_id = (
            self.get_list_id(
                list_name
            )
        )

        if not isinstance(
            fields,
            dict,
        ) or not fields:
            raise SharePointClientError(
                "fields debe contener "
                "datos."
            )

        return (
            self._graph
            .post(
                "/sites/"
                f"{site_id}/lists/"
                f"{list_id}/items",
                json_body={
                    "fields":
                        dict(fields)
                },
            )
        )

    def update_item_fields(
        self,
        list_name,
        item_id,
        fields,
        *,
        etag=None,
    ):
        site_id = (
            self.get_site_id()
        )

        list_id = (
            self.get_list_id(
                list_name
            )
        )

        item_id_value = (
            self._required(
                item_id,
                "item_id",
            )
        )

        if not isinstance(
            fields,
            dict,
        ) or not fields:
            raise SharePointClientError(
                "fields debe contener "
                "datos."
            )

        headers = {}

        if etag:
            headers[
                "If-Match"
            ] = str(
                etag
            )

        return (
            self._graph
            .patch(
                "/sites/"
                f"{site_id}/lists/"
                f"{list_id}/items/"
                f"{item_id_value}/fields",
                json_body=dict(
                    fields
                ),
                extra_headers=(
                    headers
                    or None
                ),
            )
        )

    def delete_item(
        self,
        list_name,
        item_id,
        *,
        etag=None,
    ):
        site_id = (
            self.get_site_id()
        )

        list_id = (
            self.get_list_id(
                list_name
            )
        )

        item_id_value = (
            self._required(
                item_id,
                "item_id",
            )
        )

        headers = {}

        if etag:
            headers[
                "If-Match"
            ] = str(
                etag
            )

        return (
            self._graph
            .delete(
                "/sites/"
                f"{site_id}/lists/"
                f"{list_id}/items/"
                f"{item_id_value}",
                extra_headers=(
                    headers
                    or None
                ),
            )
        )

    @staticmethod
    def _normalize_site_path(
        value,
    ) -> str:
        text = (
            SharePointClient
            ._required(
                value,
                "SHAREPOINT_SITE_PATH",
            )
        )

        if not text.startswith(
            "/"
        ):
            text = "/" + text

        return text.rstrip(
            "/"
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
            raise SharePointClientError(
                f"{name} no esta "
                "configurado."
            )

        return text
