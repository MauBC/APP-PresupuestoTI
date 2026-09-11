# Legacy code

Esta carpeta contiene scripts historicos conservados como referencia.

NO forma parte de la arquitectura activa de APP-PresupuestoTI.

## scriptLimpieza

Implementacion original utilizada para:

- limpiar archivos CSV/Excel;
- convertir importes;
- validar columnas;
- cargar datos a BigQuery;
- comparar tablas;
- diagnosticar diferencias.

Su funcionalidad fue reemplazada por la implementacion actual:

database/bootstrap/

Los nuevos desarrollos NO deben importar codigo desde legacy/scriptLimpieza.

## migrate_persistence.py

Script experimental utilizado durante las primeras pruebas de persistencia
sobre una tabla BigQuery antigua.

El script intentaba migrar una tabla existente agregando columnas tecnicas y
creando estructuras auxiliares.

No corresponde al esquema actual.

La tabla actual:

proyecto-yvette.presupuesto_ti.presupuesto_2026

fue creada directamente mediante el nuevo bootstrap con 67 columnas,
incluyendo desde el inicio:

- row_id
- habilitado
- version
- created_at
- created_by
- updated_at
- updated_by

Los nuevos desarrollos de persistencia deben implementarse en:

database/persistence/

y no deben depender de legacy/migrate_persistence.py.