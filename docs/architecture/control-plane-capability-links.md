# Links de capabilities con el control-plane

## Propósito

El registro `specs/integration/capability-links.yaml` mantiene un vínculo activo
entre las capabilities de audiencias de `sst-chatbot` y el capability padre ya
conocido por `4uentes-orchestor`. Cada link conserva el owner spec, el estado
local y la evidencia técnica que el control-plane puede reconciliar.

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

El link local está activo y fue establecido sobre la reconciliación conocida
`CR-SST-0082`. Las tres capabilities nuevas todavía esperan la próxima
reconciliación del control-plane y por eso no tienen IDs remotos inventados.

No existe push remoto automático porque `4uentes-orchestor` no publicó un
transporte de ingestión para evidencia de child capabilities. Hasta que exista,
el gate garantiza integridad y visibilidad en el manifiesto, pero no afirma una
entrega remota que no ocurrió.
