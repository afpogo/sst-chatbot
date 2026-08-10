# Policies

## Propósito

Este repositorio adopta el common policy runtime canónico de
`4uentes-ards-core`. La adopción local gobierna cómo trabajan los agentes y
cómo se conserva la autoridad documental, sin reemplazar contratos funcionales
ni decisiones del control-plane.

El registro machine-readable vive en `specs/integration/policies.yaml` y los
manifests individuales en `specs/policies/`.

## Policies adoptadas

- `agent-model-selection-policy`
- `agent-resource-degradation-policy`
- `agent-task-atomization-policy`
- `agent-delegation-policy`
- `agent-context-management-policy`
- `agent-architecture-boundary-policy`
- `human-doc-language`
- `owner-documentation-authority-policy`
- `control-plane-link-policy`
- `http-qa-harness-policy`

`http-qa-harness-policy` quedó adoptada por `CR-SST-0168`: el endpoint interno
de turnos tiene un caso reproducible en `httpPruebas/chat-turns.http` y pruebas
automatizadas en `tests/test_chat_http_runtime.py`.

## Reglas locales

- Los nombres de modelos son aliases resueltos por el entorno.
- La documentación humana nueva se escribe en español; IDs, schemas, comandos
  y contratos técnicos conservan su forma estable.
- Este repo es autoridad sobre su runtime, capabilities outbound, specs y tests.
- `4uentes-orchestor` conserva request lifecycle, evidencia central y estado
  reconciliado, pero no reemplaza la documentación owner de este repo.
- `orchestrator_link` se mantiene como alias local de `control_plane_link`.
- El chatbot produce propuestas e intents; no ejecuta operaciones productivas.

## Estado

La adopción local está materializada para la aplicabilidad actual y pendiente
de una nueva reconciliación del control-plane.
