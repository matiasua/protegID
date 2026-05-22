# Seguridad

## Reglas iniciales

- No guardar datos medicos en QR.
- No subir secretos al repositorio.
- No hardcodear credenciales.
- No loguear datos medicos o sensibles.
- No usar IDs secuenciales como identificadores publicos.
- No exponer IDs internos en URLs publicas.
- Mantener configuracion sensible mediante variables de entorno.

## Variables de entorno

`.env.example` contiene valores de ejemplo para desarrollo local. Cada entorno debe definir sus propios valores reales fuera del control de versiones.

## Estado actual

Este setup no implementa autenticacion, autorizacion, perfiles medicos ni persistencia de datos de negocio.
