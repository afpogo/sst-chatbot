# Política de selección de modelo y subagentes

## Propósito

Este anexo aplica `agent-model-selection-policy` al trabajo con Codex dentro de
`sst-chatbot`. Decide cómo ejecutar tareas; no autoriza cambios funcionales ni
reemplaza contracts, ownership, requests o validaciones ARDS/SDD.

## Clasificación de tareas

Antes de planificar se usa una de estas categorías:

- `short-defined-task`
- `long-context-task`
- `complex-high-risk-task`

La clasificación considera alcance, cantidad de capas, riesgo, seguridad,
contratos e incertidumbre.

## Disponibilidad de recursos

`resource_level` acepta `very-low`, `low`, `normal` y `high`. Si no existe una
señal explícita, se usa:

```yaml
resource_level: "normal"
resource_source: "default"
```

Los nombres de modelos son aliases configurables. Si un alias no está
disponible, debe registrarse el fallback; no se degrada silenciosamente trabajo
sensible.

## Routing

| Recursos | Tarea corta | Contexto largo | Alto riesgo |
| --- | --- | --- | --- |
| `high` | `gpt-5.6-sol/high` | `gpt-5.6-sol/high` | `gpt-5.6-sol/max` |
| `normal` | `gpt-5.6-sol/low` | `gpt-5.6-sol/high` | `gpt-5.6-sol/max` |
| `low` | `gpt-5.3-spark/low` | `gpt-5.4-fast-high/high` | `gpt-5.5/high` |
| `very-low` | Spark sólo para bajo riesgo | atomizar o bloquear | bloquear |

## Delegación

El plan debe registrar clasificación, drivers, perfil primario, fallback y
deployment de subagentes. Se delegan únicamente unidades acotadas, con contexto
definido y salida verificable. Arquitectura, seguridad y contratos sensibles
permanecen bajo revisión del agente principal.

Si el runtime no permite subagentes, se usa secuencia local con el perfil de
mayor razonamiento disponible y se registra el fallback.

## Boundary ARDS/SDD

Esta policy sólo gobierna la ejecución agentic. No permite redefinir el runtime
del orquestador, la autoridad de repos funcionales, el canon de
`4uentes-ards-core` ni capabilities cross-repo sin el lifecycle correspondiente.
