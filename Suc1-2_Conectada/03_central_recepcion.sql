-- EJECUTAR SOLO EN CENTRAL. La sucursal invoca estos procedimientos via CENTRAL_LINK.
CREATE OR REPLACE PACKAGE pkg_recepcion AS
 PROCEDURE recibir_cliente(p_id VARCHAR2,p_cedula VARCHAR2,p_nombre VARCHAR2,
   p_telefono VARCHAR2,p_nodo VARCHAR2);
 PROCEDURE recibir_factura(p_factura NUMBER,p_cedula VARCHAR2,p_fecha TIMESTAMP,
   p_total NUMBER,p_nodo VARCHAR2);
 PROCEDURE recibir_detalle(p_nodo VARCHAR2,p_detalle NUMBER,p_factura NUMBER,
   p_producto NUMBER,p_cantidad NUMBER,p_subtotal NUMBER);
END pkg_recepcion;
/
CREATE OR REPLACE PACKAGE BODY pkg_recepcion AS
 PROCEDURE recibir_cliente(p_id VARCHAR2,p_cedula VARCHAR2,p_nombre VARCHAR2,
   p_telefono VARCHAR2,p_nodo VARCHAR2) IS
 BEGIN
   -- Cedula = identidad de la persona; no se sobrescribe el perfil existente.
   MERGE INTO clientes c USING (SELECT p_cedula cedula FROM dual) s
   ON (c.cedula=s.cedula)
   WHEN NOT MATCHED THEN INSERT(id_cliente,cedula,nombre,telefono,nodo_origen,sincronizado)
   VALUES (p_id,p_cedula,p_nombre,p_telefono,p_nodo,1);
 END;
 PROCEDURE recibir_factura(p_factura NUMBER,p_cedula VARCHAR2,p_fecha TIMESTAMP,
   p_total NUMBER,p_nodo VARCHAR2) IS
   v_cliente clientes.id_cliente%TYPE;
   v_nodo facturas.nodo_emisor%TYPE;
 BEGIN
   SELECT id_cliente INTO v_cliente FROM clientes WHERE cedula=p_cedula;
   -- No se actualizan ventas ya recibidas; si mismo numero de otro nodo, se rechaza.
   BEGIN
     SELECT nodo_emisor INTO v_nodo FROM facturas WHERE id_factura=p_factura;
     IF v_nodo<>p_nodo THEN
       RAISE_APPLICATION_ERROR(-20010,'Colision de consecutivo entre sucursales');
     END IF;
   EXCEPTION WHEN NO_DATA_FOUND THEN NULL;
   END;
   MERGE INTO facturas f USING (SELECT p_factura id_factura FROM dual) s
   ON (f.id_factura=s.id_factura)
   WHEN NOT MATCHED THEN INSERT(id_factura,id_cliente,fecha_emision,total,nodo_emisor,sincronizado)
   VALUES(p_factura,v_cliente,p_fecha,p_total,p_nodo,1);
 END;
 PROCEDURE recibir_detalle(p_nodo VARCHAR2,p_detalle NUMBER,p_factura NUMBER,
   p_producto NUMBER,p_cantidad NUMBER,p_subtotal NUMBER) IS
   v_nodo facturas.nodo_emisor%TYPE;
 BEGIN
   SELECT nodo_emisor INTO v_nodo FROM facturas WHERE id_factura=p_factura;
   IF v_nodo<>p_nodo THEN
     RAISE_APPLICATION_ERROR(-20011,'Detalle no corresponde al nodo de factura');
   END IF;
   MERGE INTO detalle_factura d
   USING (SELECT p_nodo nodo_origen,p_detalle id_detalle_origen FROM dual) s
   ON (d.nodo_origen=s.nodo_origen AND d.id_detalle_origen=s.id_detalle_origen)
   WHEN NOT MATCHED THEN INSERT(id_factura,id_producto,cantidad,subtotal,nodo_origen,id_detalle_origen)
   VALUES(p_factura,p_producto,p_cantidad,p_subtotal,p_nodo,p_detalle);
 END;
END pkg_recepcion;
/
SHOW ERRORS PACKAGE pkg_recepcion;
SHOW ERRORS PACKAGE BODY pkg_recepcion;
