# Gobierno de audiencias y divulgación segura

## Propósito

Esta vertical convierte una identidad ya verificada por SST en contexto seguro
para el modelo. No autentica personas ni calcula permisos de negocio. Aplica una
segunda barrera determinista para impedir que datos fuera de scope o resultados
no respaldados crucen el límite del provider.

```text
principal afirmado por SST + contexto clasificado
  -> autorización y minimización determinista
  -> provider reemplazable
  -> claims estructurados
  -> validación de divulgación
  -> respuesta read-only, sin handoff
```

## Experiencia `sst_user`

El scope exige `tenant_id`, `user_id` y `application_id`. Se aceptan datos
`public`, `internal` y `private` provenientes de `sst_backend`, siempre que el
scope y los entitlements coincidan. El envelope declara explícitamente qué
campos pueden entrar al prompt; el resto se descarta.

## Experiencia `sst_stakeholder`

Sólo consume snapshots globales de `approved_analytics` clasificados como
`public` o `derived_safe`. El port analítico admite seis KPIs, período mensual y
una única dimensión `module_id` para `module_adoption`. No existen filtros
libres, consultas SQL ni navegación hacia tenants o registros individuales.

Una cohorte menor a 10 se entrega como suprimida y nunca se prepara para el
provider. El valor, definición, período, cohorte y provenance forman parte del
snapshot aprobado; cualquier claim de salida debe coincidir con él.

## Observabilidad y control-plane

Los traces y registros de auditoría contienen audiencia, versión de policy y
código de decisión, con `contains_business_data: false`. No contienen prompt,
contexto, respuesta, KPI, identificador ni credencial.

`4uentes-orchestor` recibe sólo evidencia de madurez técnica de las
capabilities. La reconciliación permanece pendiente y no se crean request IDs,
receipts ni estados de ejecución locales.
