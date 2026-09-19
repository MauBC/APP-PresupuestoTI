# Roadmap de APP-PresupuestoTI

Actualizado: 2026-09-18. Los estados distinguen implementacion de validacion
funcional; la existencia de tests no significa que todo el milestone este cerrado.

## Base de trabajo

- PR #2: consolidacion del estado probado por el usuario, ya integrado en `main`.
- PR #3: diagnostico contextual, ya integrado en `main`.
- PR #4: decisiones CEBE explicitas y mejoras del editor, ya integrado en `main`.
- Validacion de esa base: 1094 pruebas unitarias aprobadas, 18 excluidas.
- Cada mejora comienza en una rama limpia y conserva Workspace, staging,
  auditoria, batches y concurrencia optimista.
- Las mejoras siguientes parten de `main` actualizado, con PR independientes.

## Estado por milestone

| Milestone | Estado observado | Criterio de cierre pendiente |
| --- | --- | --- |
| H2C/H2D: OPEX inteligente | Diagnostico contextual y seleccion explicita de CEBE completados; restauracion exacta de decisiones y GUI verificadas | Validar recuperacion ante error y politica de microimportes de extremo a extremo |
| M8F: deshabilitar/reactivar | Soporte y pruebas existentes | Verificar circuito completo OPEX/CAPEX con auditoria y reversion |
| M10: rendimiento | Carga OPEX optimizada, cache de metadatos y benchmarks | Medir carga, filtros, agrupaciones, edicion y memoria con 50.000 filas |
| M11: Ver cambios | Mejoras implementadas | Validacion funcional de revision de lotes grandes |
| M12: historial avanzado | Contexto de negocio y tipos de operacion implementados | Confirmar criterios funcionales en ambos modulos |
| M13: dashboard | Simulacion, Top dinamico y graficos implementados | Conciliar cifras y validar filtros y uso funcional |
| M8G: altas asistidas | Base OPEX e inferencias/selecciones implementadas | Validar casos completos y cerrar alcance pendiente |
| M9: ML/FX avanzado | FX de importacion implementado | Definir edicion multimoneda, recalculo y referencia de TC auditable |
| M8E: Excel corregible | Correccion y revalidacion implementadas con pruebas | Validar visualmente errores corregibles e importacion final OPEX/CAPEX |
| M14: empaquetado | Pendiente de cierre | Distribucion y prueba en una PC sin entorno de desarrollo |
| M16F: SharePoint OPEX | Reservado para el final | Contrato, sincronizacion idempotente y conciliacion |

## Checkpoint H2D: diagnostico de errores de maestros

- Se conservan fila Excel y CECO al convertir el analisis en plan de resolucion.
- El error entregado a la interfaz incluye hoja, fila, CECO, codigo y causa.
- Se muestran hasta cinco incidencias de la hoja bloqueada y la cantidad restante.
  La excepcion conserva la lista completa para consumidores del servicio.
- Los errores de cuenta sin fila no reciben un CECO inventado.
- Se mantiene el bloqueo: el worker no emite resultado exitoso ante estos errores.
- El dialogo de avisos calcula su altura con el ancho fijo para evitar recortar
  las ultimas lineas del diagnostico.
- Validacion: 1100 pruebas unitarias aprobadas, 18 excluidas; pruebas del pipeline
  de maestros/plan/defaults, del mensaje entregado por el worker y de geometria
  del aviso. Render local verificado con cinco incidencias y contador de restantes.
- Limite: el flujo sigue deteniendose en la primera hoja bloqueada. El resumen no
  es un reporte exportable de todas las hojas.

## Siguientes checkpoints propuestos

1. H2D/M9: completar politica de precision para edicion/redistribucion y validar
   round-trip real de BigQuery en una prueba controlada. La importacion inteligente
   hasta staging ya conserva nueve decimales en los casos automatizados.
2. M8G/M8E: validacion funcional de altas asistidas y correccion Excel.
3. M10, M9 y M14: rendimiento, edicion multimoneda y distribucion de la aplicacion.
4. M16F: SharePoint OPEX, al final.

## Checkpoint H2C/H2D: decisiones explicitas y GUI

- Un CEBE con varias alternativas oficiales queda pendiente; no se elige la
  primera opcion en el servicio ni en el combo. La importacion no genera filas
  hasta completar las decisiones.
- La decision conserva todos los atributos CEBE y la categoria de la cuenta.
  Reabrir el dialogo no cambia una seleccion por otra con el mismo nombre o tipo.
- El editor muestra pendientes por pestaña y un contador general; Aplicar
  decisiones solo se habilita al completar todas las selecciones.
- Los detalles completos de cuenta/CEBE se muestran debajo del selector. Los
  textos largos se ajustan y el contenido se recorre con scroll en tamaño reducido.
- Validacion: 1105 pruebas unitarias aprobadas, 18 excluidas; prueba del flujo
  completo de preparacion pendiente -> seleccion -> generacion y total USD;
  pruebas GUI de bloqueo, restauracion y scroll. Renders locales revisados en
  840x620 y 720x520. No se ejecutaron escrituras en BigQuery ni SharePoint.
- La politica de precision monetaria no cambia en este checkpoint.

## Checkpoint H2D/M9: microimportes y correccion de residuales

- El plan valida totales con los mismos nueve decimales que la distribucion
  inteligente. Ya no acepta perder un microimporte por comparar a centavos.
- El ruido binario de Excel (por ejemplo 5954.3499999999985) sigue normalizandose.
- La correccion de residuales no genera filas negativas cuando muchos redondeos
  superan el saldo de la fila de mayor peso. Aplica al motor compartido tanto a
  centavos como a nueve decimales, conservando el comportamiento habitual.
- La periodizacion rechaza negativos antes de redondear, incluidos valores que
  antes se convertian silenciosamente en cero.
- La tabla muestra los importes no nulos menores a 0.01 con sus decimales y
  ofrece el valor almacenado completo en el tooltip de las columnas numericas.
- Validacion: 1125 pruebas unitarias aprobadas, 18 excluidas. Casos ANUAL/MENSUAL
  recorren seleccion, distribucion, FX, filas, Workspace, batch, JSON de staging
  y exportacion Excel. Se verifican totales mensuales/anuales y no negatividad.
  Render local de la tabla revisado y diff --check limpio.
- Limites: no se escribio en BigQuery; staging se verifico localmente. Excel
  sigue usando celdas numericas y no garantiza todos los digitos de valores de
  gran magnitud. No cambia la politica de edicion/redistribucion a centavos ni
  se declara cerrada la edicion multimoneda M9.

## Recomendaciones adicionales por priorizar

- Recuperacion de borradores del Workspace con revalidacion de versiones.
- Aviso de importaciones potencialmente duplicadas.
- Trazabilidad de archivo, hoja, fila, maestros, decisiones y TC utilizados.
- Reporte exportable de incidencias de todas las hojas.
- Conciliacion por hoja y moneda, incluidos microimportes.

Estas recomendaciones no se consideran implementadas ni sustituyen el roadmap.
