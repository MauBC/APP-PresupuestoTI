# Roadmap de APP-PresupuestoTI

Actualizado: 2026-09-19. Los estados distinguen implementacion de validacion
funcional; la existencia de tests no significa que todo el milestone este cerrado.

## Base de trabajo

- PR #2: consolidacion del estado probado por el usuario, ya integrado en `main`.
- PR #3: diagnostico contextual, ya integrado en `main`.
- PR #4: decisiones CEBE explicitas y mejoras del editor, ya integrado en `main`.
- PR #5: microimportes y residuales no negativos, ya integrado en `main`.
- PR #6: correccion Excel asincrona y bloqueo de resultados desactualizados,
  ya integrado en `main`.
- PR #7: conservar exclusiones al revalidar Excel, ya integrado en `main`.
- PR #8: exclusion masiva Excel optimizada, ya integrado en `main`.
- Validacion del ultimo checkpoint: 1183 pruebas unitarias aprobadas, 18 excluidas.
- Cada mejora comienza en una rama limpia y conserva Workspace, staging,
  auditoria, batches y concurrencia optimista.
- Las mejoras siguientes parten de `main` actualizado, con PR independientes.

## Estado por milestone

| Milestone | Estado observado | Criterio de cierre pendiente |
| --- | --- | --- |
| H2C/H2D: OPEX inteligente | Diagnostico contextual y seleccion explicita de CEBE completados; restauracion exacta de decisiones y GUI verificadas | Validar recuperacion ante error y politica de microimportes de extremo a extremo |
| M8F: deshabilitar/reactivar | Soporte y pruebas existentes | Verificar circuito completo OPEX/CAPEX con auditoria y reversion |
| M10: rendimiento | Exclusion Excel y paginacion optimizadas; carga, filtros de estado y agrupaciones del Workspace medidos con 50.000 filas sinteticas OPEX/CAPEX | Completar mediciones con datos representativos, edicion, memoria total y respuesta de la GUI |
| M11: Ver cambios | Mejoras implementadas | Validacion funcional de revision de lotes grandes |
| M12: historial avanzado | Contexto de negocio y tipos de operacion implementados | Confirmar criterios funcionales en ambos modulos |
| M13: dashboard | Simulacion, Top dinamico y graficos implementados | Conciliar cifras y validar filtros y uso funcional |
| M8G: altas asistidas | Base OPEX e inferencias/selecciones implementadas; reservado para el final por indicacion del usuario | Validar casos completos y cerrar alcance pendiente |
| M9: ML/FX avanzado | FX de importacion implementado | Definir edicion multimoneda, recalculo y referencia de TC auditable |
| M8E: Excel corregible | Correccion asincrona, bloqueo de vistas desactualizadas y persistencia de exclusiones verificados en OPEX/CAPEX | Completar revision funcional con archivos reales OPEX/CAPEX |
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
2. M8E: validacion funcional de correccion Excel con archivos reales.
3. M10, M9 y M14: rendimiento, edicion multimoneda y distribucion de la aplicacion.
4. M8G: altas asistidas, reservadas para el final por indicacion del usuario.
5. M16F: SharePoint OPEX, al final.

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

## Checkpoint M8E: correccion Excel consistente y asincrona

- Revalidar correcciones utiliza el worker existente, con copia de las
  correcciones y una ventana de progreso que mantiene activa la interfaz.
- Cancelar espera a que termine la lectura en curso y descarta su resultado;
  no destruye un hilo activo ni utiliza terminacion forzada.
- Un fallo o cancelacion conserva las correcciones para reintentar y bloquea
  la importacion de la vista previa anterior. Solo un resultado validado vuelve
  a habilitar la importacion.
- Cada pestaña de incidencias utiliza su propia seleccion y modelo; Errores y
  Advertencias ya no consultan accidentalmente la tabla de Informativos.
- Validacion: 1133 pruebas unitarias aprobadas, 18 excluidas. Pruebas de GUI,
  temporizador activo durante revalidacion, cancelacion segura, errores,
  reintento y agregado exclusivo del resultado corregido al Workspace.
  Renders locales de progreso y bloqueo revisados; diff --check limpio.
- No se modifican los Excel originales ni se escribe en BigQuery/SharePoint.
- M8G (altas asistidas) queda reservado para el final por indicacion del usuario.

## Checkpoint M8E: conservar exclusiones al revalidar

- Las filas excluidas se identifican por su fila Excel, conservando la decision
  aunque se regenere el identificador tecnico o cambie el orden de la vista previa.
- Revalidar, cancelar y reintentar conserva las exclusiones junto a las correcciones.
  Solo las filas incluidas del resultado validado pasan al Workspace.
- Una fila excluida temporalmente ausente mantiene su estado si vuelve a aparecer.
  Incluir todas restablece explicitamente las exclusiones de esta importacion.
- Validacion: 1139 pruebas unitarias aprobadas, 18 excluidas; casos OPEX/CAPEX
  de filtros, orden, cambio de identificadores, ausencia de filas y reintentos.
- Pendiente de cierre M8E: recorrido funcional con archivos reales de ambos modulos.
  Este checkpoint no realiza escrituras en BigQuery ni SharePoint.

## Checkpoint M10: seleccion masiva en la vista previa Excel

- Excluir seleccionadas actualiza el modelo y notifica a la interfaz una sola vez.
  Los contadores se actualizan incrementalmente, sin recorrer todas las filas por
  cada cambio. Incluir todas utiliza la misma operacion en bloque.
- La GUI obtiene las filas desde los rangos seleccionados, evitando que Qt revise
  cada columna por cada fila. Conserva el mapeo correcto con filtros y ordenacion.
- Medicion local sintetica: en un modelo de 50.000 filas, excluir 5.000 con el
  recuento conectado paso de 26,73 s a 0,004 s aproximadamente. Es una medicion
  del modelo, no del tiempo total de la interfaz.
- En el dialogo completo, una vez aplicada la operacion en bloque, cambiar la
  lectura de seleccion de Qt redujo excluir 50.000 filas de 30,21 a 1,79 s en
  OPEX y de 23,92 a 1,89 s en CAPEX. Restaurar todas tomo 1,35 y 1,54 s.
- Benchmark reproducible sin servicios externos:
  `python -m tools.benchmark_import_selection --rows 50000 --dialog`.
  Usa filas sinteticas con CECO; no representa un archivo de negocio completo.
  La memoria informada corresponde solo a asignaciones Python durante la carga
  del modelo, no al consumo total de Qt ni de la aplicacion.
- Validacion: 1143 pruebas unitarias aprobadas, 18 excluidas; seleccion filtrada
  y ordenada OPEX/CAPEX, duplicados, indices invalidos, contadores, restauracion
  y bloqueo de importacion sin filas incluidas. Render local de 50.000 filas revisado.
- M10 sigue abierto: faltan filtros, agrupaciones, edicion y memoria del Workspace
  con datos representativos. Las altas asistidas siguen reservadas para el final.

## Checkpoint M10: paginacion del Workspace

- Sin filtro de estado, la pagina usa el total conocido del Workspace y deja de
  consumir filas al completar el rango solicitado. Conserva el orden de sesion.
- Con filtro, calcula el total exacto en un recorrido y conserva una ventana
  acotada de filas para devolver la ultima pagina si la solicitada ya no existe.
  Se elimina la consulta recursiva que repetia todo el recorrido.
- No se agregan caches de resultados: ediciones, habilitaciones y recargas se
  reflejan en la siguiente consulta. Las filas entregadas siguen siendo copias.
- Benchmark offline: `python -m tools.benchmark_workspace_analysis --rows 50000`.
  Mediana de cinco consultas por operacion, paginas de 100 filas. Datos sinteticos
  con dimensiones, importes Decimal de nueve decimales y 20% de filas deshabilitadas.

| Operacion | OPEX antes / despues | CAPEX antes / despues |
| --- | --- | --- |
| Primera pagina sin filtro | 20,66 / 0,78 ms | 35,92 / 1,48 ms |
| Pagina fuera de rango sin filtro | 34,71 / 6,63 ms | 81,00 / 8,64 ms |
| Pagina fuera de rango, habilitadas | 49,35 / 21,48 ms | 51,19 / 26,34 ms |

- Referencias de la ejecucion final: carga local 2,54 s OPEX / 4,13 s CAPEX;
  agrupacion por pais y presupuestador 0,27 / 0,30 s; agrupacion con filtro de
  pais 0,18 / 0,18 s. Estas operaciones no se modificaron en este checkpoint.
- El filtro de estado sigue requiriendo recorrer todas las filas para contar;
  no se promete una mejora en todas las consultas filtradas. iter_rows conserva
  su ordenacion de identificadores y su coste de memoria existente.
- Validacion: 1183 pruebas unitarias aprobadas, 18 excluidas; ambos modulos,
  paginas exactas/parciales/vacias, filtros, retorno a ultima pagina, conteo de
  recorridos, edicion, cambios de estado y recarga. No se consultaron servicios
  externos ni se modificaron BigQuery/SharePoint.
- M10 continua abierto para memoria total, edicion y mediciones funcionales de
  GUI con datos representativos. M8G permanece reservado para el final.
