# Policies

## Proposito

Esta carpeta contiene la lectura humana de las policies operativas adoptadas por
el repo.

El registry machine-readable vive en:

- specs/integration/policies.yaml

Estas policies se heredan desde 4uentes-ards-core y se aplican localmente sin
reemplazar contratos funcionales, capabilities, ownership ni arquitectura de
producto.

## Policies adoptadas

- gent-model-selection-policy
- gent-resource-degradation-policy
- gent-task-atomization-policy
- gent-delegation-policy
- gent-context-management-policy
- gent-architecture-boundary-policy

## Reglas locales

- Resolver aliases de modelos segun la configuracion local del repo.
- Registrar gaps o excepciones locales antes de contradecir una policy core.
- Mantener alineados AGENTS.md, specs/00-index.yaml y specs/integration/policies.yaml.

## Pendientes

No hay excepciones locales abiertas para esta adopcion minima. Si aparece una,
registrarla en el lifecycle del orquestador y en artefactos ARDS/SDD locales.
