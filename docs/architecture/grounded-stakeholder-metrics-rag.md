# RAG gobernado para métricas de stakeholders

## Propósito

CR-SST-0156 amplía la lectura segura de métricas globales de SST con contexto
metodológico citable. La fuente de métricas continúa siendo
`approved_analytics`; el RAG sólo aporta definiciones y metodología aprobada y
nunca calcula, corrige ni sustituye el valor del KPI.

## Flujo obligatorio

```text
PrincipalContext validado por SST + MetricQuery cerrada
  -> MetricSnapshot desde approved_analytics
  -> supresión por cohorte y validación de provenance
  -> candidatos desde approved_methodology
  -> policy gate por métrica, estado, indexabilidad, clasificación y entitlement
  -> ranking exclusivo de metodología ya autorizada
  -> provider port con snapshot + contexto metodológico mínimo
  -> validación exacta de MetricClaim contra el snapshot
  -> validación de citas contra la metodología recuperada
  -> respuesta grounded o resultado fail-closed
```

El retriever no otorga acceso. El proveedor no recibe el principal, el tenant,
los entitlements ni registros analíticos crudos.

## Contratos y autoridad

- `MetricSnapshot` es la única autoridad para valores, periodo, dimensión y
  provenance analítica.
- `MethodologyRecord` es un candidato controlado por el owner y nunca contiene
  valores de KPI.
- `AuthorizedMethodology` es la única proyección que puede llegar al retriever
  y al provider.
- `StakeholderGroundedAnswer` separa narrativa sin números, claims
  estructurados y referencias metodológicas.
- `StakeholderRagResult` devuelve el snapshot validado, claims exactos, citas y
  un trace metadata-only.

## Seguridad

- Sólo se admite metodología activa, indexable, de la misma métrica y
  clasificada `public` o `derived_safe`.
- `restricted` y `secret` son denegaciones absolutas.
- La cohorte mínima sigue siendo 10 y se aplica antes de consultar metodología
  o provider.
- No se admiten tenant drill-down, personas, registros crudos, SQL ni filtros
  libres.
- Una claim que difiere del snapshot o una cita no recuperada falla cerrada.
- La narrativa del provider no puede contener valores numéricos; los números
  sólo viajan en `MetricClaim` y se verifican exactamente.
- Los errores de source, retriever y provider se convierten en códigos
  sanitizados. El trace no contiene preguntas, valores, contenido ni
  identificadores de persona o tenant.

## Estado de integración

La implementación usa ports y fakes deterministas. No conecta una base
analítica, vector store, proveedor LLM, HTTP, Socket.IO ni handoffs. Esas
integraciones requieren requests posteriores con owner de datos, transporte,
custodia de secretos y límites operativos explícitos.

## Validación

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_stakeholder_rag.py tests/test_stakeholder_rag_specs.py
.\.venv\Scripts\python.exe scripts/smoke_stakeholder_rag.py
.\.venv\Scripts\python.exe scripts/check.py
```

El smoke verifica un caso grounded y confirma que una cohorte pequeña detiene
el flujo antes de methodology source, retriever y provider.
