# Smoke de conexion con proveedor LLM simulado

## Alcance

Este smoke valida el boundary de `CR-SST-0168` sin usar credenciales ni cuota de
un proveedor externo. El escenario ejecuta dos conexiones HTTP locales:

1. cliente SST simulado -> `POST /internal/v1/chat/turns` con M2M;
2. `ProviderChatRuntime` -> proveedor OpenAI-compatible simulado con SSE.

El resultado SSE se transforma en eventos NDJSON `delta`, `delta`, `completed`.
La solicitud al proveedor contiene texto y `correlation_id`, pero no contiene
`user_id`, `account_id` ni `tenant_id`.

## Ejecucion

```powershell
.\.venv\Scripts\python.exe scripts\smoke_llm_provider_connection.py
```

El comando tambien forma parte de `scripts/check.py` para mantener el escenario
reproducible.

## Criterio

- `ok=true`;
- protocolo simulado `openai-compatible-sse`;
- salida `application/x-ndjson`;
- eventos ordenados `delta`, `delta`, `completed`;
- `principal_forwarded=false`.

## Limite

La validacion prueba conectividad, streaming y minimizacion de contexto contra
un servidor local. No prueba disponibilidad, latencia, cuotas, autenticacion ni
comportamiento de un proveedor LLM productivo.
