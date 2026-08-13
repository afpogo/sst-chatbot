# Links de capabilities con el control-plane

## Propósito

El registro `specs/integration/capability-links.yaml` mantiene vínculos activos
entre las capabilities de `sst-chatbot` y sus capabilities padre conocidas por
`4uentes-orchestor`. Cada link conserva el owner spec, el estado local y la
evidencia técnica que el control-plane puede reconciliar.

## Movimiento de capabilities

El contrato considera movimiento a la creación de una capability o al cambio
de su estado, contrato o evidencia. `scripts/check.py` valida en cada gate que:

- el link y el owner spec existen;
- el estado declarado coincide con el estado owner;
- el inventario outbound coincide con el stream de sincronización;
- el `movement_digest` coincide con el owner spec, su código, sus tests y el feature state;
- `execution_authority` es `none`;
- `contains_business_data` es `false`.

Esto evita que un cambio quede fuera del manifiesto técnico versionado. El modo
de entrega actual es `owner-manifest-pull`: el control-plane puede consumir el
manifiesto del repositorio y reconciliarlo.

## Límite actual

El link local fue establecido por `CR-SST-0082`. Las capabilities de audiencia
conservan ese parent y CR-SST-0155 agrega el movimiento owner de
`retrieval-augmented-generation` hacia el estado `sst-user-ards-rag` ya
registrado por el control-plane. La evidencia queda lista para readback sin
inventar IDs remotos ni afirmar una entrega automática.

No existe push remoto automático porque `4uentes-orchestor` no publicó un
transporte de ingestión para evidencia de child capabilities. Hasta que exista,
el gate garantiza integridad y visibilidad en el manifiesto, pero no afirma una
entrega remota que no ocurrió.

El stream contiene únicamente madurez técnica. Preguntas, chunks privados,
respuestas grounded, citas con datos de negocio e identificadores de
tenant/persona están prohibidos.
