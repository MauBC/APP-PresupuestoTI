from decimal import Decimal


# Precision interna de la insercion inteligente OPEX.
# BigQuery NUMERIC soporta hasta 9 decimales.
OPEX_SMART_MONEY_QUANTUM = Decimal(
    "0.000000001"
)
