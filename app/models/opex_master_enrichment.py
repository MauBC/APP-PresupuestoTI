from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class OpexCecoMasterEnrichment:
    ceco_prefix: str
    sociedad: str
    compania: str
    pais: str
    ceco: str
    centro_beneficio: str | None
    gyp: str | None
    desc_cebe: str | None
    macroservicio_cg: str | None
    tipo_servicio_cg: str | None
    region_cg: str | None
    sede_cg: str | None
    segmentacion: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class OpexMasterEnrichment:
    numero_cuenta: str
    nombre_cuenta: str
    categoria_gasto: str
    atributo_2: str

    ceco_prefix: str
    sociedad: str
    compania: str
    pais: str

    ceco: str
    centro_beneficio: str | None
    gyp: str | None

    desc_cebe: str | None
    macroservicio_cg: str | None
    tipo_servicio_cg: str | None
    region_cg: str | None
    sede_cg: str | None
    segmentacion: str | None
