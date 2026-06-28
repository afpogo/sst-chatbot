# Playbook 05: Ciclo De Vida De Prompts

## Objetivo
Guiar a humanos, agentes y futuros nodos del sistema para generar, versionar,
manipular, validar y consumir prompts privados de SST sin dispersar texto de
prompt en codigo de agente ni exponerlo mediante almacenamiento propietario de
LangSmith.

## Politica De Idioma
La documentacion humana se escribe en espanol. Los nombres de contrato,
filenames, ids, campos YAML, schemas, clases, funciones y terminos operativos se
mantienen en ingles tecnico cuando forman parte de la interfaz estable.

Ejemplos: `prompt_id`, `trace_policy`, `metadata_only`,
`provider_cache_policy`, `PromptRenderRequest`, `render_prompt`.

## Principios
- El repo es la fuente privada de prompts en V1.
- LangSmith no es fuente de prompts.
- El prompt YAML define texto, mensajes, variables y metadata de compatibilidad.
- La memoria, retrieval, provider config y ejecucion de modelo viven fuera del
  prompt YAML.
- El provider recibe mensajes renderizados, no archivos YAML.
- La traza operativa usa metadata; no debe incluir cuerpos renderizados ni
  valores de variables.
- Todo cambio de prompt es un cambio de comportamiento y requiere validacion.

## Estados Del Prompt
- `draft`: prompt en desarrollo o pendiente de evidencia suficiente.
- `stable`: prompt aprobado para uso regular por agentes o workflows.
- `deprecated`: prompt mantenido por compatibilidad, pero no recomendado para
  nuevos usos.

Un agente no debe cambiar `stable` a otro estado sin evidencia documental o una
request explicita. Si necesita modificar comportamiento de un prompt estable,
debe crear una nueva version.

## Ciclo De Vida
1. Descubrimiento: identificar capability, agente, tarea, variables necesarias,
   sensibilidad de datos y providers/modelos compatibles.
2. Diseno: definir `id`, `version`, `status`, mensajes, variables, defaults,
   `visibility`, `trace_policy`, `provider_cache_policy`,
   `compatible_providers` y `compatible_models`.
3. Autoria: crear o editar el YAML bajo `src/app/prompts/catalog/`.
4. Registro: agregar el prompt a `CATALOG_PATHS` en
   `src/app/prompts/registry.py`.
5. Validacion estatica: confirmar placeholders simples, variables declaradas,
   roles permitidos y metadata obligatoria.
6. Render local: llamar `render_prompt(...)` con variables fake o mockeadas y
   revisar que el resultado esperado este en `messages`.
7. Ensamblado: convertir con `to_langchain_messages(...)` solo cuando el flujo
   necesita objetos de LangChain.
8. Ejecucion: pasar mensajes renderizados al adapter del provider. El adapter
   no debe leer YAML ni resolver prompts por su cuenta.
9. Trazabilidad: persistir u observar `trace_metadata` con `prompt_id`,
   `prompt_version`, `prompt_hash`, provider, modelo y nombres de variables.
10. Validacion final: ejecutar pruebas y checks ARDS/SDD.
11. Promocion: mover de `draft` a `stable` solo con tests y evidencia
    suficiente.
12. Deprecacion: marcar versiones antiguas como `deprecated` despues de migrar
    consumidores.

## Contrato YAML
Cada prompt de catalogo debe definir:

```yaml
id: task.example
version: "1"
status: draft
description: Prompt funcional para clasificar una solicitud.
trace_policy: metadata_only
visibility: internal_private
provider_cache_policy: none
compatible_providers:
  - any
compatible_models:
  - any
variables:
  - name: user_request
    type: string
    required: true
    sensitive: true
    description: Solicitud original del usuario.
messages:
  - role: system
    template: |
      Classify the user request into one known capability.
  - role: human
    template: |
      User request:
      {user_request}
```

Roles permitidos: `system`, `human`, `assistant`.

Tipos de variable permitidos: `string`, `integer`, `number`, `boolean`, `list`,
`object`.

## Reglas De Manipulacion
- Crear un prompt nuevo cuando aparece una capability o tarea nueva.
- Crear una nueva `version` cuando cambia comportamiento observable.
- Editar la misma version solo para cambios no funcionales mientras esta en
  `draft`.
- No borrar una version consumida por tests, specs o agentes sin deprecarla
  antes.
- No usar placeholders con atributos, indices, conversiones o format specs.
  Permitido: `{tenant_id}`. No permitido: `{user.name}`, `{items[0]}`,
  `{score:.2f}`.
- Escapar llaves JSON literales como `{{` y `}}`.
- Declarar como `sensitive: true` toda variable que pueda contener tenant,
  request de usuario, contexto privado, memoria o datos operativos.
- Mantener `provider_cache_policy: none` para prompts internos salvo revision
  explicita.
- No introducir secrets, credenciales, tokens, paths locales privados o datos
  reales de usuario en ejemplos de prompts.

## Flujo Tecnico
Crear o actualizar el YAML:

```text
src/app/prompts/catalog/
```

Registrar el prompt:

```python
CATALOG_PATHS = {
    "task.example": PROMPTS_DIR / "catalog" / "tasks" / "example.yaml",
}
```

Renderizar desde codigo:

```python
from app.prompts import PromptRenderRequest
from app.prompts import render_prompt
from app.prompts import to_langchain_messages

rendered = render_prompt(
    PromptRenderRequest(
        prompt_id="task.example",
        version="1",
        provider="openai",
        model="gpt-5.4-mini",
        variables={"user_request": "Crear un agente para resumir bitacoras."},
    )
)

messages = to_langchain_messages(rendered)
metadata = rendered.trace_metadata
```

`messages` puede ir al provider o chain. `metadata` puede ir a observabilidad,
auditoria o evidencia. El cuerpo renderizado y los valores de variables no deben
agregarse intencionalmente a metadata de traza.

## Comandos

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_prompt_engine.py
.\.venv\Scripts\python.exe scripts\ards_check.py
```

Validacion completa:

```powershell
.\.venv\Scripts\python.exe scripts\check.py
```

## Resultado Esperado
El prompt carga mediante registry explicito, valida variables declaradas,
renderiza con inputs locales, se puede ensamblar para LangChain y emite
metadata-only trace information.

## Problemas Comunes
- Un placeholder como `{tenant_id}` debe tener una variable declarada.
- Inputs de render con claves no declaradas son rechazados.
- El YAML debe usar roles `system`, `human` o `assistant`.
- JSON literal dentro de templates debe escapar llaves como `{{` y `}}`.
- Provider API options y reglas de memory retrieval no pertenecen al YAML.
- Si existe mas de una version para el mismo `id`, el consumidor debe pedir
  `version` explicitamente.

## Checklist Para Agentes
- Confirmar si el cambio es nuevo prompt, nueva version, edicion draft o
  deprecacion.
- Mantener cuerpos de prompt solo bajo `src/app/prompts/catalog/`.
- Registrar el prompt en `CATALOG_PATHS`.
- Agregar o actualizar tests cuando cambia comportamiento.
- Verificar que `trace_policy` sea `metadata_only`.
- Verificar que `visibility` sea `internal_private`.
- Verificar que prompts internos usen `provider_cache_policy: none`.
- No enviar prompt bodies ni valores sensibles a metadata u observabilidad.
- Ejecutar validacion antes de cerrar la tarea.
