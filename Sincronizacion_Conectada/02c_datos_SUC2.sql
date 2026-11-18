-- SOLO SUC2: ejecutar despues del DDL, antes de sincronizar.
INSERT INTO config_nodo VALUES ('SUC2');
INSERT INTO clientes(id_cliente,cedula,nombre,telefono,nodo_origen)
VALUES('1001-SUC2','204560789','Carlos Gomez Brenes','8333-4455','SUC2');
INSERT INTO facturas(id_factura,id_cliente,total,nodo_emisor)
VALUES(200001,'1001-SUC2',3200,'SUC2');
COMMIT;
-- DESPUES de sincronizar productos por primera vez ejecutar:
-- INSERT INTO detalle_factura(id_factura,id_producto,cantidad,subtotal) VALUES(200001,2,1,3200);
-- COMMIT;
