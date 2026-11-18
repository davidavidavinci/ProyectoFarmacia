-- EJECUTAR EN SUC1 Y SUC2, nunca en SUC3.
-- Primero crear DB link desde cada sucursal hacia CENTRAL con datos reales:
-- CREATE DATABASE LINK CENTRAL_LINK
-- CONNECT TO FARMACIA IDENTIFIED BY "TU_CLAVE"
-- USING '//IP_DE_CENTRAL:1521/XEPDB1';
-- Verificar ANTES de crear el paquete: SELECT 1 FROM dual@CENTRAL_LINK;
-- Los usuarios precisan CREATE DATABASE LINK y privilegios sobre el paquete remoto.

CREATE OR REPLACE PACKAGE pkg_sync_conectada AS
 PROCEDURE sincronizar_productos;
 PROCEDURE sincronizar_clientes;
 PROCEDURE sincronizar_facturas;
 PROCEDURE distribuir_clientes;
 PROCEDURE sincronizacion_completa;
END pkg_sync_conectada;
/
CREATE OR REPLACE PACKAGE BODY pkg_sync_conectada AS
 PROCEDURE registrar(p_proceso VARCHAR2,p_estado VARCHAR2,p_cantidad NUMBER,p_mensaje VARCHAR2) IS
   v_nodo config_nodo.id_nodo%TYPE;
 BEGIN
  SELECT id_nodo INTO v_nodo FROM config_nodo;
  INSERT INTO bitacora_sincronizacion(nodo,proceso,estado,registros,mensaje)
  VALUES (v_nodo,p_proceso,p_estado,p_cantidad,SUBSTR(p_mensaje,1,1000));
 END;
 PROCEDURE sincronizar_productos IS
   v_cantidad NUMBER;
 BEGIN
   -- El stock es local de cada farmacia y NO se sobreescribe con el stock central.
   MERGE INTO productos p USING (
     SELECT id_producto,codigo_barra,nombre_medicamento,precio_unitario,fecha_actualizacion
     FROM productos@CENTRAL_LINK
   ) c ON (p.id_producto=c.id_producto)
   WHEN MATCHED THEN UPDATE SET
     p.nombre_medicamento=c.nombre_medicamento,
     p.precio_unitario=c.precio_unitario,
     p.fecha_actualizacion=c.fecha_actualizacion
   WHERE p.fecha_actualizacion<c.fecha_actualizacion
   WHEN NOT MATCHED THEN INSERT
     (id_producto,codigo_barra,nombre_medicamento,precio_unitario,stock_actual,fecha_actualizacion)
     VALUES(c.id_producto,c.codigo_barra,c.nombre_medicamento,c.precio_unitario,0,c.fecha_actualizacion);
   v_cantidad:=SQL%ROWCOUNT;
   registrar('PRODUCTOS','EXITO',v_cantidad,'Catalogo actualizado; stock local conservado');
   COMMIT;
 EXCEPTION WHEN OTHERS THEN
   ROLLBACK;
   registrar('PRODUCTOS','ERROR',0,SQLERRM); COMMIT; RAISE;
 END;
 PROCEDURE sincronizar_clientes IS
   v_cantidad NUMBER:=0;
 BEGIN
   FOR c IN (SELECT id_cliente,cedula,nombre,telefono,nodo_origen
             FROM clientes WHERE sincronizado=0) LOOP
     pkg_recepcion.recibir_cliente@CENTRAL_LINK(c.id_cliente,c.cedula,c.nombre,c.telefono,c.nodo_origen);
     UPDATE clientes SET sincronizado=1 WHERE id_cliente=c.id_cliente;
     v_cantidad:=v_cantidad+1;
   END LOOP;
   registrar('SUBIR_CLIENTES','EXITO',v_cantidad,'Se enviaron clientes a CENTRAL');
   COMMIT;
 EXCEPTION WHEN OTHERS THEN
   ROLLBACK;
   registrar('SUBIR_CLIENTES','ERROR',0,SQLERRM); COMMIT; RAISE;
 END;
 PROCEDURE sincronizar_facturas IS
   v_cantidad NUMBER:=0;
   v_cedula clientes.cedula%TYPE;
 BEGIN
   FOR f IN (SELECT * FROM facturas WHERE sincronizado=0 ORDER BY id_factura) LOOP
     SELECT cedula INTO v_cedula FROM clientes WHERE id_cliente=f.id_cliente;
     pkg_recepcion.recibir_factura@CENTRAL_LINK(f.id_factura,v_cedula,f.fecha_emision,f.total,f.nodo_emisor);
     FOR d IN (SELECT * FROM detalle_factura WHERE id_factura=f.id_factura) LOOP
       pkg_recepcion.recibir_detalle@CENTRAL_LINK(f.nodo_emisor,d.id_detalle,f.id_factura,
          d.id_producto,d.cantidad,d.subtotal);
     END LOOP;
     UPDATE facturas SET sincronizado=1 WHERE id_factura=f.id_factura;
     v_cantidad:=v_cantidad+1;
   END LOOP;
   registrar('SUBIR_FACTURAS','EXITO',v_cantidad,'Facturas y detalles enviados');
   COMMIT;
 EXCEPTION WHEN OTHERS THEN
   ROLLBACK;
   registrar('SUBIR_FACTURAS','ERROR',0,SQLERRM); COMMIT; RAISE;
 END;
 PROCEDURE distribuir_clientes IS
   v_cantidad NUMBER;
 BEGIN
   -- En retorno al nodo de origen: la cedula ya existe, por lo tanto no se toca.
   -- Si dos sucursales crearon el mismo cliente con IDs distintos, se conserva el
   -- ID local y las facturas locales siguen siendo validas.
   MERGE INTO clientes c USING
    (SELECT id_cliente,cedula,nombre,telefono,nodo_origen FROM clientes@CENTRAL_LINK) r
   ON (c.cedula=r.cedula)
   WHEN NOT MATCHED THEN INSERT(id_cliente,cedula,nombre,telefono,nodo_origen,sincronizado)
   VALUES(r.id_cliente,r.cedula,r.nombre,r.telefono,r.nodo_origen,1);
   v_cantidad:=SQL%ROWCOUNT;
   registrar('BAJAR_CLIENTES','EXITO',v_cantidad,'Padron global distribuido');
   COMMIT;
 EXCEPTION WHEN OTHERS THEN
   ROLLBACK;
   registrar('BAJAR_CLIENTES','ERROR',0,SQLERRM); COMMIT; RAISE;
 END;
 PROCEDURE sincronizacion_completa IS
   v_nodo config_nodo.id_nodo%TYPE;
 BEGIN
   sincronizar_productos;
   sincronizar_clientes;
   sincronizar_facturas;
   distribuir_clientes;
   SELECT id_nodo INTO v_nodo FROM config_nodo;
   UPDATE catalogo_nodos@CENTRAL_LINK
      SET ultima_sincronizacion=SYSTIMESTAMP WHERE id_nodo=v_nodo;
   COMMIT;
 END;
END pkg_sync_conectada;
/
SHOW ERRORS PACKAGE pkg_sync_conectada;
SHOW ERRORS PACKAGE BODY pkg_sync_conectada;
