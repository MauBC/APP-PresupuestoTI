# CAPEX - Estado operativo

## Estado actual

CAPEX esta integrado como modulo real de APP-PresupuestoTI.

La aplicacion permite cambiar entre:

- OPEX
- CAPEX

Ambos modulos reutilizan el mismo motor de Workspace,
persistencia, concurrencia, auditoria, historial y reversion.

## BigQuery

Proyecto:

    proyecto-yvette

Dataset:

    presupuesto_ti

Tabla OPEX:

    presupuesto_2026

Tabla CAPEX:

    capex_2027

Persistencia compartida:

    presupuesto_change_batches
    presupuesto_audit
    presupuesto_change_staging

La separacion de operaciones se realiza mediante:

    budget_module = OPEX
    budget_module = CAPEX

## CAPEX actual

La tabla CAPEX utilizada actualmente contiene:

    173 filas

La estructura corresponde al contrato PB 2027.

Los datos cargados actualmente son datos de simulacion
correspondientes al periodo 2026.

Esto es intencional.

No ejecutar una carga completa CAPEX con --apply sobre
capex_2027 mientras la tabla contenga estas filas.

## Regla financiera actual

Por ahora CAPEX funciona igual que OPEX:

    SOLO USD ES EDITABLE

Columnas editables:

    enero_usd
    febrero_usd
    marzo_usd
    abril_usd
    mayo_usd
    junio_usd
    julio_usd
    agosto_usd
    setiembre_usd
    octubre_usd
    noviembre_usd
    diciembre_usd
    anio_usd

Las columnas ML se mantienen almacenadas pero no son
modificadas por el Workspace.

La columna:

    moneda_facturacion

tambien permanece intacta durante una edicion USD.

## Mejora futura: moneda local

Posteriormente la logica cambiara para que el usuario
modifique moneda local.

La columna:

    moneda_facturacion

determinara la moneda correspondiente de cada fila.

Se utilizara un tipo de cambio estandarizado para todo
el presupuesto.

Flujo esperado:

    modificar ML
        ->
    identificar moneda_facturacion
        ->
    aplicar FX oficial
        ->
    calcular USD
        ->
    guardar ML + USD + referencia FX
        ->
    audit

La arquitectura transaccional actual debe reutilizarse.

## Persistencia

Cada guardado genera un batch auditable.

Flujo:

    Workspace
        ->
    get_pending_changes
        ->
    batch PENDING
        ->
    staging
        ->
    optimistic concurrency
        ->
    audit
        ->
    MERGE
        ->
    version + 1
        ->
    APPLIED
        ->
    cleanup staging
        ->
    reload selectivo

No se permite persistencia parcial.

## Concurrencia

Si el Workspace cargo:

    version = N

y BigQuery posteriormente contiene:

    version = N + 1

el guardado termina:

    CONFLICT

No se sobrescribe silenciosamente otra modificacion.

Los cambios locales permanecen disponibles.

## Reversion

La reversion utiliza una operacion compensatoria.

Ejemplo:

    100 -> 125
    version 1 -> 2

Reversion:

    125 -> 100
    version 2 -> 3

No se elimina el audit original.

No se decrementa version.

El nuevo batch contiene:

    reverted_batch_id = batch original

## Validaciones realizadas

Suite unitaria:

    498 passed

Integracion CAPEX real:

    save
    conflict
    history
    reversal
    cleanup

Prueba GUI real:

    USD 100 -> 125 -> 100
    version 1 -> 2 -> 3

La prueba confirmo:

    ML 365 -> 365
    moneda PEN -> PEN

Al terminar el cleanup:

    capex_2027 = 173 filas

## Funciones CAPEX disponibles

Actualmente:

- carga desde BigQuery
- Dashboard
- agrupaciones
- edicion mensual USD
- edicion anual USD
- distribucion mensual
- edicion agrupada
- Ver cambios
- Undo
- Descartar
- Apply
- optimistic concurrency
- audit
- historial
- detalle de batches
- reversion
- reload selectivo
- cambio OPEX / CAPEX

## Pendientes

Prioridad siguiente:

1. distribucion mensual avanzada por grupos
2. altas masivas y autocomplete
3. moneda local + FX
4. carga Excel desde GUI
5. altas/reactivaciones
6. roles y permisos
7. Dashboard avanzado
8. mejoras de Ver cambios
9. rendimiento
10. empaquetado final
