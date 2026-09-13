# HU-AT16 — Auditar cambios de taxonomía

**Épica:** AT — Admin Taxonomía  
**Sprint:** 0/4

## Historia de usuario

**Como:** Admin  
**Quiero:** Ver el historial de cambios en todas las taxonomías  
**Para:** Cumplir con RG-07 (auditoría inmutable) y RG-35 (versionado)

## Criterios de aceptación

- `GET /api/v1/admin/taxonomy/audit?scope=models|orchestrators|domains&from=&to=` requiere rol `admin`.
- Muestra quién, qué, cuándo, versión anterior, versión nueva y motivo.
- El resultado es paginado.
- Se puede exportar a CSV.
- El historial es de solo lectura y no se puede editar ni borrar.
