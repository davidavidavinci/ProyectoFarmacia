# Persona 2 — Sincronización conectada (Oracle XE)

## Objetivo
Sincronizar SUC1 y SUC2 con CENTRAL. Los productos/precios bajan; los clientes, facturas y detalles suben; después bajan los clientes consolidados. SUC3 no utiliza enlaces de base de datos: Persona 3 implementa su intercambio por correo.

## Correcciones al modelo original
1. `clientes.id_cliente` y `facturas.id_cliente` son VARCHAR2(30); los valores como `1001-SUC1` NO son números.
2. Cada detalle de factura conserva un identificador local (`id_detalle`) y la central registra el par único `(nodo_origen, id_detalle_origen)`, evitando colisiones entre identidades de distintas sucursales.
3. Se agrega `bitacora_sincronizacion` para errores y ejecuciones; `config_nodo` identifica cada base. La estructura DDL es idéntica en los cuatro nodos.
4. Las semillas se separan por nodo. No se copia a cada sucursal el histórico de todas las demás.
5. Se conserva el `id_cliente` local si la cédula ya existe; CENTRAL usa la cédula para identificar al cliente canónico. La factura entrante se relaciona con el ID central, sin alterar las facturas locales.
6. `stock_actual` se mantiene localmente en cada sucursal; solo catálogo y precios se distribuyen desde CENTRAL.

## Instalación paso a paso (base nueva, sin tablas preexistentes)
**No ejecutar 01 sobre una base que ya tenga estas tablas**. Respaldar o acordar migración con Persona 1.

1. Ejecutar `01_estructura_corregida_TODOS.sql` en CENTRAL, SUC1, SUC2 y SUC3 (cada una por separado).
2. Ejecutar `02a_datos_CENTRAL.sql` SOLO en CENTRAL; `02b_datos_SUC1.sql` SOLO en SUC1; `02c_datos_SUC2.sql` SOLO en SUC2. Persona 3 ejecuta `02d_config_SUC3_PARA_PERSONA3.sql` en SUC3.
3. Ejecutar `03_central_recepcion.sql` SOLO en CENTRAL. Verificar `SHOW ERRORS` sin errores.
4. En SUC1 y SUC2, crear `CENTRAL_LINK` hacia la IP, servicio (ej. XEPDB1) y credenciales reales de CENTRAL; plantilla comentada al principio de `04_sucursal_link_Y_paquete.sql`.
   * El usuario Oracle de las sucursales necesita `CREATE DATABASE LINK` y `CREATE JOB`; el usuario del link debe poder ejecutar `pkg_recepcion`, leer `productos`/`clientes` y actualizar `catalogo_nodos` si se añade ese paso.
   * Probar `SELECT 1 FROM dual@CENTRAL_LINK;` y `SELECT COUNT(*) FROM productos@CENTRAL_LINK;`.
5. Ejecutar `04_sucursal_link_Y_paquete.sql` en SUC1 y SUC2, luego comprobar `SHOW ERRORS`.
6. En SUC1 y SUC2 ejecutar `BEGIN pkg_sync_conectada.sincronizar_productos; END; /`. Comprobar que aparecen los 4 productos y sus IDs.
7. Insertar los detalles de prueba comentados al final de `02b` y `02c`; ejecutar COMMIT en cada sucursal.
8. En SUC1 y SUC2 ejecutar `BEGIN pkg_sync_conectada.sincronizacion_completa; END; /`. Probar vistas de CENTRAL y de la bitácora como describe `06_pruebas_y_evidencias.sql`.
9. Repetir el paso 8 para demostrar idempotencia: no deben aumentar los conteos de facturas y detalles en CENTRAL.
10. Ejecutar `05_automatizacion_SUC1_SUC2.sql` en ambas sucursales. El JOB se crea **deshabilitado**. Activarlo solo después de probar manualmente.


## Evidencias mínimas para el documento
- Capturas de SELECT de productos, clientes, facturas y detalle_factura ANTES en ambos nodos, y DESPUÉS en CENTRAL.
- Captura de `bitacora_sincronizacion` después de ejecutar y repetir.
- Captura de modificación de precio en CENTRAL, cambio reflejado en SUC1/SUC2 y stock local conservado.
- Captura de cliente con misma cédula e IDs distintos en ambas sucursales: una fila en CENTRAL, facturas vinculadas correctamente.
- Captura de fallo de enlace: la sucursal sigue registrando facturas sin conexión, queda `sincronizado=0`, y al restablecer el enlace suben.
- Captura del estado y próxima ejecución de `USER_SCHEDULER_JOBS`.