"""TavoDebate - Articulado del Proyecto de Acuerdo activo.

El Presidente del Concejo usa este articulado para abrir votaciones por
artículo y para compilar el texto final aprobado. Cuando cambie el tema
del ejercicio, actualiza este módulo.
"""

PROYECTO_ID = "001-2026"
PROYECTO_TITULO = (
    "Proyecto de Acuerdo No. 001 de 2026 — Actualización catastral "
    "multipropósito en los municipios de Cundinamarca"
)

ARTICULOS = [
    {
        "numero": 1,
        "titulo": "Adopción de la actualización catastral multipropósito",
        "texto": (
            "Adóptese la actualización catastral multipropósito como base "
            "para el cálculo del impuesto predial a partir del año "
            "gravable 2027."
        ),
    },
    {
        "numero": 2,
        "titulo": "Régimen de transición",
        "texto": (
            "Establézcase un régimen de transición de 3 años con "
            "incrementos graduales: Año 1 (30%), Año 2 (60%), Año 3 "
            "(100%) del nuevo avalúo."
        ),
    },
    {
        "numero": 3,
        "titulo": "Fondo de alivio tributario",
        "texto": (
            "Créese un fondo de alivio tributario para predios rurales "
            "menores a 5 hectáreas cuyos propietarios estén en SISBEN A o B."
        ),
    },
    {
        "numero": 4,
        "titulo": "Destinación del mayor recaudo",
        "texto": (
            "Destínese el 40% del mayor recaudo a inversión en vías "
            "terciarias, agua potable y conectividad rural del municipio."
        ),
    },
    {
        "numero": 5,
        "titulo": "Rendición de cuentas",
        "texto": (
            "La administración municipal rendirá informe trimestral al "
            "Concejo sobre recaudo, reclamos y ejecución del fondo de "
            "alivio."
        ),
    },
]


def get_articulo(numero: int) -> dict | None:
    for art in ARTICULOS:
        if art["numero"] == numero:
            return art
    return None
