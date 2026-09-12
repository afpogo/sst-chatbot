# CR-SST-0225 — Contrato owner del ejecutor de artículos

Rol documental primario: evidencia de unidad contractual. Owner:
`sst-chatbot`. Estado: preparado localmente, sin runtime ni publicación.

Este slice define una ejecución síncrona y acotada protegida por
`article-processing:execute`, más las lecturas y propuestas hacia Bend bajo
`article-processing:read` y `article-processing:write`. Bend continúa siendo la
única autoridad durable.

No se modificaron módulos Python, prompts, providers, endpoints, tests,
variables, secretos, infraestructura ni despliegues. Las specs y el mapa se
mantienen en `draft` hasta una autorización posterior.

Referencias:

- `specs/capabilities/article-processing-execution.yaml`;
- `specs/integrations/sst-article-processing-handoff.yaml`;
- `specs/architecture/article-processing-pipeline.yaml`;
- `docs/architecture/article-processing-pipeline.md`.
