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
    centro_beneficio: str
    gyp: str
    desc_cebe: str
    macroservicio_cg: str
    tipo_servicio_cg: str
    region_cg: str
    sede_cg: str
    segmentacion: str


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
    centro_beneficio: str
    gyp: str

    desc_cebe: str
    macroservicio_cg: str
    tipo_servicio_cg: str
    region_cg: str
    sede_cg: str
    segmentacion: str
