import re

from app.models.opex_master_data import (
    OpexAccountMasterRecord,
    OpexCebeMasterRecord,
    OpexMasterDataSnapshot,
    OpexRecoverableMasterRecord,
)
from app.models.opex_master_enrichment import (
    OpexMasterEnrichment,
)
from app.services.opex_master_data_loader import (
    normalize_master_code,
)


GYP_BY_FINAL_DIGIT = {
    "1": "COSTOS VARIABLES",
    "2": "COSTOS FIJOS DIRECTOS",
    "3": "COSTOS FIJOS INDIRECTOS",
    "4": "GASTOS DE ADMINISTRACI\u00D3N",
    "5": "GASTOS DE VENTAS",
    "7": "OTROS I/E OPERATIVOS",
}


class OpexMasterEnrichmentError(
    ValueError
):
    def __init__(
        self,
        code,
        message,
        *,
        key=None,
    ):
        super().__init__(
            message
        )

        self.code = code
        self.key = key


class OpexMasterEnrichmentService:
    def __init__(
        self,
        snapshot: OpexMasterDataSnapshot,
    ):
        self._snapshot = snapshot

    @staticmethod
    def normalize_ceco(
        value,
    ) -> str:
        if value is None:
            raise OpexMasterEnrichmentError(
                "INVALID_CECO",
                "CECO esta vacio.",
            )

        ceco = str(
            value
        ).strip().upper()

        if not ceco:
            raise OpexMasterEnrichmentError(
                "INVALID_CECO",
                "CECO esta vacio.",
            )

        if (
            re.fullmatch(
                r"[A-Z0-9]+",
                ceco,
            )
            is None
        ):
            raise OpexMasterEnrichmentError(
                "INVALID_CECO",
                "CECO contiene caracteres "
                "no permitidos: "
                f"{ceco}",
                key=ceco,
            )

        if len(
            ceco
        ) < 2:
            raise OpexMasterEnrichmentError(
                "INVALID_CECO",
                "CECO es demasiado corto: "
                f"{ceco}",
                key=ceco,
            )

        return ceco

    @classmethod
    def derive_gyp_from_ceco(
        cls,
        value,
    ) -> str:
        ceco = cls.normalize_ceco(
            value
        )

        final_digit = ceco[-1]

        try:
            return GYP_BY_FINAL_DIGIT[
                final_digit
            ]
        except KeyError as exc:
            raise OpexMasterEnrichmentError(
                "INVALID_GYP_DIGIT",
                "El ultimo caracter del CECO "
                f"{ceco} es {final_digit}. "
                "No existe una regla GyP "
                "para ese valor.",
                key=ceco,
            ) from exc

    @classmethod
    def derive_cebe_from_ceco(
        cls,
        value,
    ) -> str:
        ceco = cls.normalize_ceco(
            value
        )

        # Validar tambien el ultimo digito.
        cls.derive_gyp_from_ceco(
            ceco
        )

        return (
            ceco[:-1]
            + "0"
        )

    @staticmethod
    def _required(
        value,
        *,
        code,
        field,
        key,
    ) -> str:
        if value is None:
            raise OpexMasterEnrichmentError(
                code,
                f"{field} esta vacio para "
                f"{key}.",
                key=key,
            )

        text = str(
            value
        ).strip()

        if not text:
            raise OpexMasterEnrichmentError(
                code,
                f"{field} esta vacio para "
                f"{key}.",
                key=key,
            )

        return text

    @staticmethod
    def _unique_records(
        records,
    ):
        result = []

        for record in records:
            if record not in result:
                result.append(
                    record
                )

        return tuple(
            result
        )

    def account_options(
        self,
        numero_cuenta,
    ) -> tuple[
        OpexAccountMasterRecord,
        ...,
    ]:
        key = normalize_master_code(
            numero_cuenta
        )

        if not key:
            return ()

        conflict = (
            self._snapshot
            .account_conflicts
            .get(
                key
            )
        )

        if conflict is not None:
            return self._unique_records(
                conflict.records
            )

        record = (
            self._snapshot
            .accounts
            .get(
                key
            )
        )

        if record is None:
            return ()

        return (
            record,
        )

    def cebe_options(
        self,
        centro_beneficio,
    ) -> tuple[
        OpexCebeMasterRecord,
        ...,
    ]:
        key = normalize_master_code(
            centro_beneficio
        )

        if not key:
            return ()

        conflict = (
            self._snapshot
            .cebe_conflicts
            .get(
                key
            )
        )

        if conflict is not None:
            return self._unique_records(
                conflict.records
            )

        record = (
            self._snapshot
            .cebes
            .get(
                key
            )
        )

        if record is None:
            return ()

        return (
            record,
        )

    def resolve_account(
        self,
        numero_cuenta,
    ) -> OpexAccountMasterRecord:
        key = normalize_master_code(
            numero_cuenta
        )

        if (
            not key
            or not key.isdigit()
        ):
            raise OpexMasterEnrichmentError(
                "INVALID_ACCOUNT",
                "Numero de cuenta invalido: "
                f"{numero_cuenta!r}.",
                key=key,
            )

        if (
            key
            in self._snapshot.account_conflicts
        ):
            options = self.account_options(
                key
            )

            raise OpexMasterEnrichmentError(
                "ACCOUNT_AMBIGUOUS",
                f"La cuenta {key} tiene "
                f"{len(options)} definiciones "
                "distintas en CUENTA.xlsx.",
                key=key,
            )

        record = (
            self._snapshot
            .accounts
            .get(
                key
            )
        )

        if record is None:
            raise OpexMasterEnrichmentError(
                "ACCOUNT_NOT_FOUND",
                f"La cuenta {key} no existe "
                "en CUENTA.xlsx.",
                key=key,
            )

        self._required(
            record.nombre_cuenta,
            code="ACCOUNT_DATA_MISSING",
            field="Nombre Cuenta",
            key=key,
        )

        self._required(
            record.categoria_gasto,
            code="ACCOUNT_DATA_MISSING",
            field="Categoria de Gasto",
            key=key,
        )

        self._required(
            record.atributo_2,
            code="ACCOUNT_DATA_MISSING",
            field="Atributo 2",
            key=key,
        )

        return record

    @staticmethod
    def _prefix_aliases(
        key,
    ):
        aliases = {
            key,
        }

        # Los maestros usan 1, 4 y 5,
        # mientras los CECO pueden iniciar
        # con 01, 04 y 05.
        if (
            key.isdigit()
            and len(key) == 1
        ):
            aliases.add(
                key.zfill(2)
            )

        return aliases

    def resolve_recoverable(
        self,
        ceco,
    ) -> tuple[
        str,
        OpexRecoverableMasterRecord,
    ]:
        normalized = self.normalize_ceco(
            ceco
        )

        keys = (
            set(
                self._snapshot.recoverables
            )
            |
            set(
                self._snapshot
                .recoverable_conflicts
            )
        )

        matches = []

        for key in keys:
            for alias in self._prefix_aliases(
                key
            ):
                if normalized.startswith(
                    alias
                ):
                    matches.append(
                        (
                            len(alias),
                            key,
                            alias,
                        )
                    )

        if not matches:
            raise OpexMasterEnrichmentError(
                "RECOVERABLE_NOT_FOUND",
                "No existe un prefijo de "
                "RECUPERABLES.xlsx para "
                f"el CECO {normalized}.",
                key=normalized,
            )

        max_length = max(
            item[0]
            for item in matches
        )

        winners = {
            (
                key,
                alias,
            )
            for length, key, alias
            in matches
            if length == max_length
        }

        winner_keys = {
            key
            for key, _
            in winners
        }

        if len(
            winner_keys
        ) != 1:
            raise OpexMasterEnrichmentError(
                "RECOVERABLE_PREFIX_AMBIGUOUS",
                "El CECO "
                f"{normalized} coincide con "
                "mas de un prefijo recuperable: "
                + ", ".join(
                    sorted(
                        winner_keys
                    )
                ),
                key=normalized,
            )

        master_key = next(
            iter(
                winner_keys
            )
        )

        if (
            master_key
            in self._snapshot
            .recoverable_conflicts
        ):
            raise OpexMasterEnrichmentError(
                "RECOVERABLE_AMBIGUOUS",
                "El prefijo recuperable "
                f"{master_key} tiene varias "
                "definiciones.",
                key=master_key,
            )

        record = (
            self._snapshot
            .recoverables[
                master_key
            ]
        )

        self._required(
            record.sociedad,
            code="RECOVERABLE_DATA_MISSING",
            field="Sociedad",
            key=master_key,
        )

        self._required(
            record.compania,
            code="RECOVERABLE_DATA_MISSING",
            field="Descripcion Sociedad",
            key=master_key,
        )

        self._required(
            record.pais,
            code="RECOVERABLE_DATA_MISSING",
            field="Pais",
            key=master_key,
        )

        return (
            master_key,
            record,
        )

    def resolve_cebe(
        self,
        centro_beneficio,
    ) -> OpexCebeMasterRecord:
        key = normalize_master_code(
            centro_beneficio
        )

        if not key:
            raise OpexMasterEnrichmentError(
                "INVALID_CEBE",
                "CEBE esta vacio.",
            )

        if (
            key
            in self._snapshot.cebe_conflicts
        ):
            options = self.cebe_options(
                key
            )

            raise OpexMasterEnrichmentError(
                "CEBE_AMBIGUOUS",
                f"El CEBE {key} tiene "
                f"{len(options)} definiciones "
                "distintas en CEBE.xlsx.",
                key=key,
            )

        record = (
            self._snapshot
            .cebes
            .get(
                key
            )
        )

        if record is None:
            raise OpexMasterEnrichmentError(
                "CEBE_NOT_FOUND",
                f"El CEBE {key} no existe "
                "en CEBE.xlsx.",
                key=key,
            )

        fields = (
            (
                record.desc_cebe,
                "Desc_CeBe",
            ),
            (
                record.macroservicio_cg,
                "Macroservicio CG",
            ),
            (
                record.tipo_servicio_cg,
                "Tipo Servicio CG",
            ),
            (
                record.region_cg,
                "Region CG",
            ),
            (
                record.sede_cg,
                "Sede CG",
            ),
            (
                record.segmentacion,
                "Seg Rs",
            ),
        )

        for value, field in fields:
            self._required(
                value,
                code="CEBE_DATA_MISSING",
                field=field,
                key=key,
            )

        return record

    def enrich(
        self,
        *,
        numero_cuenta,
        ceco,
    ) -> OpexMasterEnrichment:
        normalized_ceco = (
            self.normalize_ceco(
                ceco
            )
        )

        account = self.resolve_account(
            numero_cuenta
        )

        gyp = self.derive_gyp_from_ceco(
            normalized_ceco
        )

        centro_beneficio = (
            self.derive_cebe_from_ceco(
                normalized_ceco
            )
        )

        (
            prefix,
            recoverable,
        ) = self.resolve_recoverable(
            normalized_ceco
        )

        cebe = self.resolve_cebe(
            centro_beneficio
        )

        return OpexMasterEnrichment(
            numero_cuenta=(
                account.numero_cuenta
            ),
            nombre_cuenta=self._required(
                account.nombre_cuenta,
                code="ACCOUNT_DATA_MISSING",
                field="Nombre Cuenta",
                key=account.numero_cuenta,
            ),
            categoria_gasto=self._required(
                account.categoria_gasto,
                code="ACCOUNT_DATA_MISSING",
                field="Categoria de Gasto",
                key=account.numero_cuenta,
            ),
            atributo_2=self._required(
                account.atributo_2,
                code="ACCOUNT_DATA_MISSING",
                field="Atributo 2",
                key=account.numero_cuenta,
            ),
            ceco_prefix=prefix,
            sociedad=self._required(
                recoverable.sociedad,
                code="RECOVERABLE_DATA_MISSING",
                field="Sociedad",
                key=prefix,
            ),
            compania=self._required(
                recoverable.compania,
                code="RECOVERABLE_DATA_MISSING",
                field="Descripcion Sociedad",
                key=prefix,
            ),
            pais=self._required(
                recoverable.pais,
                code="RECOVERABLE_DATA_MISSING",
                field="Pais",
                key=prefix,
            ),
            ceco=normalized_ceco,
            centro_beneficio=(
                centro_beneficio
            ),
            gyp=gyp,
            desc_cebe=self._required(
                cebe.desc_cebe,
                code="CEBE_DATA_MISSING",
                field="Desc_CeBe",
                key=centro_beneficio,
            ),
            macroservicio_cg=self._required(
                cebe.macroservicio_cg,
                code="CEBE_DATA_MISSING",
                field="Macroservicio CG",
                key=centro_beneficio,
            ),
            tipo_servicio_cg=self._required(
                cebe.tipo_servicio_cg,
                code="CEBE_DATA_MISSING",
                field="Tipo Servicio CG",
                key=centro_beneficio,
            ),
            region_cg=self._required(
                cebe.region_cg,
                code="CEBE_DATA_MISSING",
                field="Region CG",
                key=centro_beneficio,
            ),
            sede_cg=self._required(
                cebe.sede_cg,
                code="CEBE_DATA_MISSING",
                field="Sede CG",
                key=centro_beneficio,
            ),
            segmentacion=self._required(
                cebe.segmentacion,
                code="CEBE_DATA_MISSING",
                field="Seg Rs",
                key=centro_beneficio,
            ),
        )
