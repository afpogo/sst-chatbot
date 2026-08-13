# CR-SST-0155: núcleo RAG gobernado

## Decisión

Se implementó el primer corte local de RAG gobernado como un paquete
transport-neutral con fakes. La autorización sucede antes del ranking y toda
respuesta factual requiere citas verificadas contra los chunks recuperados.

## Incluido

- Contratos de scope, memoria, chunks, claims, citas, resultados y traces.
- Ports para source, retriever y provider.
- Policy fail-closed y detección credential-like.
- Retriever lexical determinista.
- Runtime con presupuesto de contexto y errores sanitizados.
- Pruebas unitarias, pruebas de specs y smoke local.

## Diferido

- Memoria canónica y base de datos.
- Vector store o embeddings.
- OpenAI u otro proveedor real.
- Integración con el endpoint HTTP y Socket.IO.
- Ingesta de chats/eventos crudos y escrituras de memoria.

La integración diferida necesita un request separado; este cambio no adquiere
ownership sobre persistencia ni transporte.
