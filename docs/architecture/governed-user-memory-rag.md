# RAG gobernado para memoria interna de usuario

## Propósito

CR-SST-0155 incorpora un núcleo de retrieval read-only para memoria interna de
usuario y artefactos curados de SST. El objetivo de esta primera fase es probar
el límite de autorización y grounding antes de conectar persistencia canónica,
un vector store, el chat realtime o un proveedor LLM real.

Este runtime no convierte ARDS/SDD de proyecto en memoria por usuario. Conserva
la separación definida por el control-plane entre memoria de lifecycle de un
repositorio y memoria funcional privada de SST.

## Orden obligatorio

```text
RetrievalScope validado por SST
  -> candidatos del source port
  -> policy gate por tenant, usuario, aplicación, entitlement,
     clasificación, fuente, estado e indexabilidad
  -> exclusión de secretos y contenido credential-like
  -> ranking de la proyección ya autorizada
  -> presupuesto de contexto
  -> provider port con contexto mínimo
  -> validación de claims y citas
  -> respuesta grounded o resultado fail-closed
```

El retriever calcula relevancia; no decide acceso. El provider genera claims;
no puede declarar como válida una cita que no pertenezca al conjunto realmente
recuperado.

## Contratos

- `RetrievalScope`: scope inmutable derivado de una identidad ya validada por
  SST. El texto del usuario nunca puede ampliarlo.
- `GovernedMemoryRecord`: candidato con scope, clasificación, eligibility y
  provenance.
- `AuthorizedChunk`: única proyección que puede cruzar hacia el retriever.
- `ProviderContext`: contenido mínimo, título y `chunk_id`; no incluye tenant,
  usuario, entitlements ni policy interna.
- `GroundedAnswer`: colección estructurada de claims, cada uno con al menos una
  cita.
- `RagResult`: respuesta, citas públicas y trace metadata-only.

## Seguridad y privacidad

- `restricted` y `secret` son denegaciones absolutas.
- Contenido parecido a credenciales se bloquea incluso si fue clasificado de
  manera incorrecta.
- Records de otro tenant, usuario o aplicación no llegan al retriever.
- Records inactivos, no indexables, sin entitlement o de una fuente no aprobada
  tampoco llegan al retriever.
- Preguntas con secretos aparentes se rechazan antes de consultar la fuente.
- Errores internos se convierten en códigos sanitizados.
- El trace contiene correlation id, código y contadores; no contiene pregunta,
  chunks, tenant, usuario ni contenido de negocio.
- El contenido recuperado se considera datos no confiables. Una instrucción de
  prompt injection dentro de un chunk no modifica policy ni scope.

## Grounding

El provider port no devuelve texto libre separado de su evidencia. Devuelve
claims estructurados y cada claim declara `citation_chunk_ids`. El runtime
verifica que todas las citas pertenezcan a los chunks recuperados; una cita
ausente o inventada produce una denegación sin exponer la salida parcial.

## Estado de integración

La implementación base vive en `src/app/governed_rag/`. CR-SST-0194 agrega en
`src/app/user_memory/` la composición con el runtime de chat, el source de Bend,
el audit de citas y el handoff de candidatos pendientes. El contrato y mapa
actuales están en
`docs/architecture/governed-user-memory-chat-integration.md`.

Siguen pendientes la publicación conjunta de los owners, el smoke cross-repo y
la selección de un provider real. El chatbot no adquiere persistencia canónica,
review de memoria ni autorización de identidad.

## Validación

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_governed_rag.py tests/test_governed_rag_specs.py
.\.venv\Scripts\python.exe scripts/smoke_governed_rag.py
.\.venv\Scripts\python.exe scripts/check.py
```

El smoke positivo recupera dos records autorizados y genera dos citas. Los
casos negativos comprueban que un record cross-tenant, un secreto y una
pregunta credential-like no llegan al provider fake.
