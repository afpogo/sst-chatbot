# ADR 0004: Audiencias y divulgación segura

- Estado: aceptada
- Fecha: 2026-08-08

## Contexto

SST necesita dos experiencias sobre el mismo núcleo de agentes. Una persona
usuaria debe poder consultar contexto propio autorizado. Un stakeholder debe
recibir únicamente métricas globales agregadas. Compartir runtime no puede
implicar compartir permisos, fuentes ni datos.

La identidad, los entitlements y el cálculo de métricas pertenecen al backend
SST. Los prompts y los providers no son autoridades de acceso. El orquestador
posee el lifecycle técnico de operaciones, pero no debe recibir consultas,
respuestas ni KPIs de negocio de estas lecturas.

## Decisión

Se adopta `PrincipalContext` como afirmación del backend SST y una clasificación
cerrada: `public`, `internal`, `private`, `derived_safe`, `restricted` y
`secret`.

La matriz V1 es:

| Audiencia | Fuente | Clasificaciones permitidas | Scope |
| --- | --- | --- | --- |
| `sst_user` | `sst_backend` | `public`, `internal`, `private` | tenant, usuario y aplicación exactos |
| `sst_stakeholder` | `approved_analytics` | `public`, `derived_safe` | aplicación global, sin tenant ni usuario |

Todo caso no enumerado se rechaza. `restricted` y `secret` están prohibidos en
forma absoluta. Un scope incompleto, una fuente desconocida, una policy version
distinta o una identidad no afirmada por SST también fallan de modo cerrado.

Antes del provider se autorizan y minimizan campos. Los traces y el audit
guardan sólo metadata de decisión. Después del provider, un guard determinista
rechaza identificadores personales, patrones de credenciales y claims de
métricas que no coincidan exactamente con snapshots aprobados.

Stakeholder V1 usa un catálogo cerrado de seis métricas mensuales. No admite
SQL, filtros libres ni drill-down por tenant. Toda cohorte menor a 10 entidades
se suprime. `module_id` es la única dimensión inicial y sólo aplica a
`module_adoption`.

Todas estas consultas son read-only y no generan handoff.

## Consecuencias

- El provider recibe menos contexto y no puede ampliar permisos mediante texto.
- La falta de provenance o una caída analítica bloquean la lectura.
- Algunas preguntas legítimas quedan fuera de V1 hasta que SST publique nuevos
  data products seguros.
- El adapter actual es fake/local; no selecciona API, base de datos ni
  transporte real.

La decisión machine-readable vive en
`specs/architecture/audience-safe-disclosure.yaml`.
