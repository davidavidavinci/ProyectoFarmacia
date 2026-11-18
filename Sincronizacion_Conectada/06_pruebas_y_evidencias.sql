-- 0. EN SUC1 y SUC2 verificar conexión:
SELECT 'CENTRAL_ACCESIBLE' estado FROM dual@CENTRAL_LINK;
-- 1. EN CENTRAL: catálogo antes
SELECT id_producto,nombre_medicamento,precio_unitario FROM productos ORDER BY id_producto;
-- 2. EN SUC1/SUC2: sincronizar solo productos, antes de cargar detalles:
BEGIN pkg_sync_conectada.sincronizar_productos; END;
/
SELECT id_producto,nombre_medicamento,precio_unitario,stock_actual FROM productos ORDER BY id_producto;
-- 3. EN SUC1: insertar cliente, factura y detalles que figuran en 02_semillas_por_nodo.sql.
-- 4. EN SUC2: repetir con sus propios datos.
-- 5. EN SUC1 y SUC2, ejecucion manual:
BEGIN pkg_sync_conectada.sincronizacion_completa; END;
/
-- 6. EN CENTRAL verificar llegada:
SELECT id_cliente,cedula,nodo_origen FROM clientes ORDER BY cedula;
SELECT id_factura,id_cliente,total,nodo_emisor FROM facturas ORDER BY id_factura;
SELECT id_factura,nodo_origen,id_detalle_origen,id_producto,cantidad
FROM detalle_factura ORDER BY id_factura,id_detalle_origen;
-- 7. EN SUC1 y SUC2 repetir el paquete para demostrar idempotencia:
BEGIN pkg_sync_conectada.sincronizacion_completa; END;
/
SELECT proceso,estado,registros,mensaje,fecha_ejecucion
FROM bitacora_sincronizacion ORDER BY id_bitacora DESC;
-- 8. EN CENTRAL: precio nuevo; en sucursal se mantiene stock local:
-- UPDATE productos SET precio_unitario=2700, fecha_actualizacion=SYSTIMESTAMP WHERE id_producto=1;
-- COMMIT;
-- EN SUC1 y SUC2:
-- BEGIN pkg_sync_conectada.sincronizar_productos; END;
-- /
-- 9. DUPLICADO CEDULA: registrar una persona en ambas sucursales
-- con igual cedula y distinto id_cliente local. Sincronizar SUC1 primero y SUC2 despues.
-- En central quedara una sola fila por cedula, y las facturas iran al id canonico.
-- 10. PARA FALLA: cortar el enlace a central, registrar factura local y verificar que
-- queda sincronizado=0; reestablecer enlace y sincronizar.
