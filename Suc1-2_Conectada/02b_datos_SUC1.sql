-- SOLO SUC1: ejecutar despues del DDL, antes de sincronizar.
INSERT INTO config_nodo VALUES ('SUC1');
INSERT INTO clientes(id_cliente,cedula,nombre,telefono,nodo_origen)
VALUES('1001-SUC1','101230456','Maria Rodriguez Perez','8811-2233','SUC1');
INSERT INTO facturas(id_factura,id_cliente,total,nodo_emisor)
VALUES(100001,'1001-SUC1',5700,'SUC1');
COMMIT;
-- DESPUES de sincronizar productos por primera vez ejecutar:
-- INSERT INTO detalle_factura(id_factura,id_producto,cantidad,subtotal) VALUES(100001,1,1,2500);
-- INSERT INTO detalle_factura(id_factura,id_producto,cantidad,subtotal) VALUES(100001,2,1,3200);
-- COMMIT;
