# Roadmap de APP-PresupuestoTI

Actualizado: 2026-09-18. Los estados distinguen implementacion de validacion
funcional; la existencia de tests no significa que todo el milestone este cerrado.

## Base de trabajo

- PR #2: consolidacion del estado probado por el usuario, desde
  `codex/consolidar-presupuesto-ti` hacia `main`.
- Validacion de esa base: 1094 pruebas unitarias aprobadas, 18 excluidas.
- Cada mejora comienza en una rama limpia y conserva Workspace, staging,
  auditoria, batches y concurrencia optimista.
- Mientras el PR #2 siga abierto, las mejoras derivadas se comparan contra
  su rama para que los PR muestren solo el cambio incremental.

## Estado por milestone

| Milestone | Estado observado | Criterio de cierre pendiente |
| --- | --- | --- |
| H2C/H2D: OPEX inteligente | Editor, workers y manejo de errores implementados; diagnostico contextual mejorado en este checkpoint | Validar decisiones ambiguas, recuperacion ante error y politica de microimportes de extremo a extremo |
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

1. H2C/H2D: comprobar decisiones explicitas de cuenta y CEBE. El servicio de
   defaults aun selecciona la primera alternativa CEBE; revisar esa conducta
   frente al requisito de decision explicita antes de dar el milestone por cerrado.
2. H2D/M9: validar microimportes, totales y precision en importacion, Workspace,
   exportacion y persistencia. El codigo usa nueve decimales en importacion
   inteligente; falta cerrar la politica de negocio y su coherencia completa.
3. M8G/M8E: validacion funcional de altas asistidas y correccion Excel.
4. M10, M9 y M14: rendimiento, edicion multimoneda y distribucion de la aplicacion.
5. M16F: SharePoint OPEX, al final.

## Recomendaciones adicionales por priorizar

- Recuperacion de borradores del Workspace con revalidacion de versiones.
- Aviso de importaciones potencialmente duplicadas.
- Trazabilidad de archivo, hoja, fila, maestros, decisiones y TC utilizados.
- Reporte exportable de incidencias de todas las hojas.
- Conciliacion por hoja y moneda, incluidos microimportes.

Estas recomendaciones no se consideran implementadas ni sustituyen el roadmap.
