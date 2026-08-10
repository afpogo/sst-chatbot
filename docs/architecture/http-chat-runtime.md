# Runtime HTTP interno de chat

El servicio expone `POST /internal/v1/chat/turns` sólo para `sst-bend`. La llamada exige un JWT M2M RS256 con audience `sst-chatbot`, scope `chat:process` y caller `sst-bend`; devuelve NDJSON ordenado con eventos `delta`, `completed` o `error`.

El contrato de aplicación vive en `ChatRuntimePort.process_turn()`: no conoce HTTP, Socket.IO ni persistencia. La implementación local `EchoChatRuntime` es deliberadamente determinista para desarrollo y smoke tests; no representa todavía la conexión a un proveedor LLM productivo.

Arranque local:

```powershell
$env:PYTHONPATH='src'
$env:AUTH_JWKS_URL='http://localhost:4000/.well-known/jwks.json'
python -m app.chat_runtime.http_server --port 8091
```

La solicitud reproducible está en `httpPruebas/chat-turns.http`.
