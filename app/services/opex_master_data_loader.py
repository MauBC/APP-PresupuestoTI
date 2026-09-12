from pathlib import Path
import re
from types import MappingProxyType
import unicodedata

import pandas as pd

from app.models.opex_master_data import (
    OpexAccountMasterRecord,
    OpexCebeMasterRecord,
    OpexMasterConflict,
    OpexMasterDataSnapshot,
    OpexMasterSource,
    OpexRecoverableMasterRecord,
)


class OpexMasterDataError(
    ValueError
):
    pass


ACCOUNT_HEADERS = {
    "numero_cuenta": (
        "CUENTA",
        "NUMERO DE CUENTA",
    ),
    "categoria_gasto": (
        "CATEGORIA GASTO",
        "CATEGORIA DE GASTO",
    ),
    "nombre_cuenta": (
        "NOMBRE CUENTA",
    ),
    "atributo_2": (
        "ATRIBUTO 2",
    ),
}


CEBE_HEADERS = {
    "centro_beneficio": (
        "CENTRO DE BENEFICIO",
    ),
    "desc_cebe": (
        "DESC CEBE",
    ),
    "macroservicio_cg": (
        "MACROSERVICIO CG",
    ),
    "tipo_servicio_cg": (
        "TIPO SERVICIO CG",
    ),
    "region_cg": (
        "REGION CG",
    ),
    "sede_cg": (
        "SEDE CG",
    ),
    "segmentacion": (
        "SEG RS",
    ),
}


RECOVERABLE_HEADERS = {
    "inicial": (
        "INICIAL",
    ),
    "sociedad": (
        "SOCIEDAD",
    ),
    "compania": (
        "DESCRIPCION SOCIEDAD",
    ),
    "pais": (
        "PAIS",
    ),
}


def normalize_master_header(
    value,
) -> str:
    if value is None:
        return ""

    text = str(
        value
    ).strip()

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(
            char
        )
    )

    text = re.sub(
        r"[_\-\s]+",
        " ",
        text,
    )

    return text.strip().upper()


def _is_blank(
    value,
) -> bool:
    if value is None:
        return True

    if isinstance(
        value,
        str,
    ):
        return not value.strip()

    try:
        return bool(
            pd.isna(
                value
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return False


def _text(
    value,
) -> str | None:
    if _is_blank(
        value
    ):
        return None

    return str(
        value
    ).strip()


def normalize_master_code(
    value,
) -> str | None:
    if _is_blank(
        value
    ):
        return None

    if isinstance(
        value,
        bool,
    ):
        return str(
            value
        ).strip().upper()

    if isinstance(
        value,
        int,
    ):
        return str(
            value
        )

    if isinstance(
        value,
        float,
    ):
        if value.is_integer():
            return str(
                int(
                    value
                )
            )

    text = str(
        value
    ).strip()

    if (
        text.endswith(
            ".0"
        )
        and text[:-2].isdigit()
    ):
        text = text[:-2]

    return text.upper()


class _LocatedTable:
    def __init__(
        self,
        *,
        dataframe,
        sheet_name,
        header_index,
        columns,
    ):
        self.dataframe = dataframe
        self.sheet_name = sheet_name
        self.header_index = header_index
        self.columns = columns


class OpexMasterDataLoader:
    def __init__(
        self,
        masters_directory,
    ):
        self._directory = (
            Path(
                masters_directory
            )
            .expanduser()
            .resolve()
        )

    def load(
        self,
    ) -> OpexMasterDataSnapshot:
        account_path = (
            self._directory
            / "CUENTA.xlsx"
        )

        cebe_path = (
            self._directory
            / "CEBE.xlsx"
        )

        recoverable_path = (
            self._directory
            / "RECUPERABLES.xlsx"
        )

        (
            accounts,
            account_conflicts,
            account_source,
        ) = self._load_accounts(
            account_path
        )

        (
            cebes,
            cebe_conflicts,
            cebe_source,
        ) = self._load_cebes(
            cebe_path
        )

        (
            recoverables,
            recoverable_conflicts,
            recoverable_source,
        ) = self._load_recoverables(
            recoverable_path
        )

        return OpexMasterDataSnapshot(
            accounts=MappingProxyType(
                accounts
            ),
            cebes=MappingProxyType(
                cebes
            ),
            recoverables=MappingProxyType(
                recoverables
            ),
            account_conflicts=MappingProxyType(
                account_conflicts
            ),
            cebe_conflicts=MappingProxyType(
                cebe_conflicts
            ),
            recoverable_conflicts=MappingProxyType(
                recoverable_conflicts
            ),
            account_source=account_source,
            cebe_source=cebe_source,
            recoverable_source=(
                recoverable_source
            ),
        )

    @staticmethod
    def _validate_file(
        path,
        master_name,
    ):
        if not path.exists():
            raise OpexMasterDataError(
                f"No existe {master_name}: "
                f"{path}"
            )

        if (
            path.suffix.lower()
            not in {
                ".xlsx",
                ".xlsm",
            }
        ):
            raise OpexMasterDataError(
                f"{master_name} debe ser "
                "XLSX o XLSM."
            )

    @classmethod
    def _locate_table(
        cls,
        path,
        *,
        master_name,
        header_aliases,
    ):
        cls._validate_file(
            path,
            master_name,
        )

        try:
            workbook = pd.ExcelFile(
                path
            )
        except Exception as exc:
            raise OpexMasterDataError(
                f"No se pudo abrir "
                f"{master_name}: {exc}"
            ) from exc

        candidates = []

        alias_sets = {
            field: {
                normalize_master_header(
                    alias
                )
                for alias
                in aliases
            }
            for field, aliases
            in header_aliases.items()
        }

        for sheet_name in (
            workbook.sheet_names
        ):
            try:
                dataframe = pd.read_excel(
                    workbook,
                    sheet_name=sheet_name,
                    header=None,
                    dtype=object,
                    keep_default_na=False,
                )
            except Exception as exc:
                raise OpexMasterDataError(
                    f"No se pudo leer "
                    f"{master_name}, hoja "
                    f"{sheet_name}: {exc}"
                ) from exc

            scan_limit = min(
                25,
                len(
                    dataframe
                ),
            )

            for row_index in range(
                scan_limit
            ):
                found = {}

                for column_index in range(
                    dataframe.shape[1]
                ):
                    header = (
                        normalize_master_header(
                            dataframe.iat[
                                row_index,
                                column_index,
                            ]
                        )
                    )

                    if not header:
                        continue

                    for field, aliases in (
                        alias_sets.items()
                    ):
                        if (
                            field not in found
                            and
                            header in aliases
                        ):
                            found[
                                field
                            ] = column_index

                if (
                    set(
                        found
                    )
                    ==
                    set(
                        header_aliases
                    )
                ):
                    candidates.append(
                        _LocatedTable(
                            dataframe=dataframe,
                            sheet_name=(
                                sheet_name
                            ),
                            header_index=(
                                row_index
                            ),
                            columns=found,
                        )
                    )

        if not candidates:
            raise OpexMasterDataError(
                f"{master_name}: no se "
                "encontro una tabla con "
                "los encabezados esperados."
            )

        if len(
            candidates
        ) > 1:
            locations = ", ".join(
                (
                    f"{candidate.sheet_name}"
                    f":fila "
                    f"{candidate.header_index + 1}"
                )
                for candidate
                in candidates
            )

            raise OpexMasterDataError(
                f"{master_name}: se "
                "encontraron varias tablas "
                "compatibles: "
                + locations
            )

        return candidates[0]

    @staticmethod
    def _row_is_empty(
        dataframe,
        row_index,
        columns,
    ):
        return all(
            _is_blank(
                dataframe.iat[
                    row_index,
                    column_index,
                ]
            )
            for column_index
            in columns.values()
        )

    @staticmethod
    def _value(
        table,
        row_index,
        field,
    ):
        return table.dataframe.iat[
            row_index,
            table.columns[
                field
            ],
        ]

    @staticmethod
    def _source(
        *,
        path,
        table,
        physical_rows,
        unique_rows,
        duplicate_rows,
        ignored_blank_key_rows=0,
        ignored_invalid_key_rows=0,
        conflict_keys=0,
    ):
        return OpexMasterSource(
            path=str(
                path
            ),
            sheet_name=(
                table.sheet_name
            ),
            header_row=(
                table.header_index
                + 1
            ),
            physical_rows=(
                physical_rows
            ),
            unique_rows=unique_rows,
            duplicate_rows=(
                duplicate_rows
            ),
            ignored_blank_key_rows=(
                ignored_blank_key_rows
            ),
            ignored_invalid_key_rows=(
                ignored_invalid_key_rows
            ),
            conflict_keys=(
                conflict_keys
            ),
        )

    @staticmethod
    def _register_record(
        *,
        key,
        record,
        location,
        records,
        record_locations,
        conflicts,
    ) -> str:
        conflict = conflicts.get(
            key
        )

        if conflict is not None:
            locations = (
                *conflict.locations,
                location,
            )

            conflict_records = (
                *conflict.records,
                record,
            )

            conflicts[key] = (
                OpexMasterConflict(
                    key=key,
                    locations=locations,
                    records=conflict_records,
                )
            )

            return "CONFLICT"

        existing = records.get(
            key
        )

        if existing is None:
            records[key] = record
            record_locations[key] = (
                location
            )

            return "NEW"

        if existing == record:
            return "DUPLICATE"

        first_location = (
            record_locations.pop(
                key
            )
        )

        records.pop(
            key
        )

        conflicts[key] = (
            OpexMasterConflict(
                key=key,
                locations=(
                    first_location,
                    location,
                ),
                records=(
                    existing,
                    record,
                ),
            )
        )

        return "CONFLICT"

    def _load_accounts(
        self,
        path,
    ):
        table = self._locate_table(
            path,
            master_name="CUENTA.xlsx",
            header_aliases=(
                ACCOUNT_HEADERS
            ),
        )

        records = {}
        record_locations = {}
        conflicts = {}
        physical = 0
        duplicates = 0
        ignored_blank_keys = 0
        ignored_invalid_keys = 0

        for row_index in range(
            table.header_index + 1,
            len(
                table.dataframe
            ),
        ):
            if self._row_is_empty(
                table.dataframe,
                row_index,
                table.columns,
            ):
                continue

            physical += 1

            excel_row = (
                row_index
                + 1
            )

            key = normalize_master_code(
                self._value(
                    table,
                    row_index,
                    "numero_cuenta",
                )
            )

            if not key:
                ignored_blank_keys += 1
                continue

            if not key.isdigit():
                ignored_invalid_keys += 1
                continue

            record = (
                OpexAccountMasterRecord(
                    numero_cuenta=key,
                    categoria_gasto=_text(
                        self._value(
                            table,
                            row_index,
                            "categoria_gasto",
                        )
                    ),
                    nombre_cuenta=_text(
                        self._value(
                            table,
                            row_index,
                            "nombre_cuenta",
                        )
                    ),
                    atributo_2=_text(
                        self._value(
                            table,
                            row_index,
                            "atributo_2",
                        )
                    ),
                )
            )

            result = self._register_record(
                key=key,
                record=record,
                location=(
                    f"{table.sheet_name}:"
                    f"{excel_row}"
                ),
                records=records,
                record_locations=(
                    record_locations
                ),
                conflicts=conflicts,
            )

            if result == "DUPLICATE":
                duplicates += 1

        if (
            not records
            and not conflicts
        ):
            raise OpexMasterDataError(
                "CUENTA.xlsx no contiene "
                "cuentas utilizables."
            )

        return (
            records,
            conflicts,
            self._source(
                path=path,
                table=table,
                physical_rows=physical,
                unique_rows=len(
                    records
                ),
                duplicate_rows=(
                    duplicates
                ),
                ignored_blank_key_rows=(
                    ignored_blank_keys
                ),
                ignored_invalid_key_rows=(
                    ignored_invalid_keys
                ),
                conflict_keys=len(
                    conflicts
                ),
            ),
        )

    def _load_cebes(
        self,
        path,
    ):
        table = self._locate_table(
            path,
            master_name="CEBE.xlsx",
            header_aliases=(
                CEBE_HEADERS
            ),
        )

        records = {}
        record_locations = {}
        conflicts = {}
        physical = 0
        duplicates = 0
        ignored_blank_keys = 0
        ignored_invalid_keys = 0

        for row_index in range(
            table.header_index + 1,
            len(
                table.dataframe
            ),
        ):
            if self._row_is_empty(
                table.dataframe,
                row_index,
                table.columns,
            ):
                continue

            physical += 1
            excel_row = (
                row_index
                + 1
            )

            key = normalize_master_code(
                self._value(
                    table,
                    row_index,
                    "centro_beneficio",
                )
            )

            if not key:
                ignored_blank_keys += 1
                continue

            if (
                re.fullmatch(
                    r"[A-Z0-9]+",
                    key,
                )
                is None
                or not key.endswith("0")
            ):
                ignored_invalid_keys += 1
                continue

            record = (
                OpexCebeMasterRecord(
                    centro_beneficio=key,
                    desc_cebe=_text(
                        self._value(
                            table,
                            row_index,
                            "desc_cebe",
                        )
                    ),
                    macroservicio_cg=_text(
                        self._value(
                            table,
                            row_index,
                            "macroservicio_cg",
                        )
                    ),
                    tipo_servicio_cg=_text(
                        self._value(
                            table,
                            row_index,
                            "tipo_servicio_cg",
                        )
                    ),
                    region_cg=_text(
                        self._value(
                            table,
                            row_index,
                            "region_cg",
                        )
                    ),
                    sede_cg=_text(
                        self._value(
                            table,
                            row_index,
                            "sede_cg",
                        )
                    ),
                    segmentacion=_text(
                        self._value(
                            table,
                            row_index,
                            "segmentacion",
                        )
                    ),
                )
            )

            result = self._register_record(
                key=key,
                record=record,
                location=(
                    f"{table.sheet_name}:"
                    f"{excel_row}"
                ),
                records=records,
                record_locations=(
                    record_locations
                ),
                conflicts=conflicts,
            )

            if result == "DUPLICATE":
                duplicates += 1

        if (
            not records
            and not conflicts
        ):
            raise OpexMasterDataError(
                "CEBE.xlsx no contiene "
                "CEBE utilizables."
            )

        return (
            records,
            conflicts,
            self._source(
                path=path,
                table=table,
                physical_rows=physical,
                unique_rows=len(
                    records
                ),
                duplicate_rows=(
                    duplicates
                ),
                ignored_blank_key_rows=(
                    ignored_blank_keys
                ),
                ignored_invalid_key_rows=(
                    ignored_invalid_keys
                ),
                conflict_keys=len(
                    conflicts
                ),
            ),
        )

    def _load_recoverables(
        self,
        path,
    ):
        table = self._locate_table(
            path,
            master_name=(
                "RECUPERABLES.xlsx"
            ),
            header_aliases=(
                RECOVERABLE_HEADERS
            ),
        )

        records = {}
        record_locations = {}
        conflicts = {}
        physical = 0
        duplicates = 0
        ignored_blank_keys = 0
        ignored_invalid_keys = 0

        for row_index in range(
            table.header_index + 1,
            len(
                table.dataframe
            ),
        ):
            if self._row_is_empty(
                table.dataframe,
                row_index,
                table.columns,
            ):
                continue

            physical += 1
            excel_row = (
                row_index
                + 1
            )

            key = normalize_master_code(
                self._value(
                    table,
                    row_index,
                    "inicial",
                )
            )

            if not key:
                ignored_blank_keys += 1
                continue

            if not key.isdigit():
                ignored_invalid_keys += 1
                continue

            record = (
                OpexRecoverableMasterRecord(
                    inicial=key,
                    sociedad=_text(
                        self._value(
                            table,
                            row_index,
                            "sociedad",
                        )
                    ),
                    compania=_text(
                        self._value(
                            table,
                            row_index,
                            "compania",
                        )
                    ),
                    pais=_text(
                        self._value(
                            table,
                            row_index,
                            "pais",
                        )
                    ),
                )
            )

            result = self._register_record(
                key=key,
                record=record,
                location=(
                    f"{table.sheet_name}:"
                    f"{excel_row}"
                ),
                records=records,
                record_locations=(
                    record_locations
                ),
                conflicts=conflicts,
            )

            if result == "DUPLICATE":
                duplicates += 1

        if (
            not records
            and not conflicts
        ):
            raise OpexMasterDataError(
                "RECUPERABLES.xlsx no "
                "contiene iniciales "
                "utilizables."
            )

        return (
            records,
            conflicts,
            self._source(
                path=path,
                table=table,
                physical_rows=physical,
                unique_rows=len(
                    records
                ),
                duplicate_rows=(
                    duplicates
                ),
                ignored_blank_key_rows=(
                    ignored_blank_keys
                ),
                ignored_invalid_key_rows=(
                    ignored_invalid_keys
                ),
                conflict_keys=len(
                    conflicts
                ),
            ),
        )
