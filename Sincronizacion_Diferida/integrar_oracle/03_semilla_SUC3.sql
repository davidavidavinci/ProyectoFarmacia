-- SOLO EN SUC3, como FARMACIA, despues del DDL comun. EJECUTAR UNA VEZ EN ESQUEMA VACIO.
INSERT INTO config_nodo(id_nodo) VALUES ('SUC3');
-- IDs explicitos y compartidos con el catalogo oficial de la CENTRAL.
INSERT INTO productos(id_producto,codigo_barra,nombre_medicamento,precio_unitario,stock_actual)
VALUES (1,'7441001230101','Acetaminofen 500mg',2500,20);
INSERT INTO productos(id_producto,codigo_barra,nombre_medicamento,precio_unitario,stock_actual)
VALUES (2,'7441001230102','Ibuprofeno 400mg',3200,15);
INSERT INTO productos(id_producto,codigo_barra,nombre_medicamento,precio_unitario,stock_actual)
VALUES (3,'7441001230103','Amoxicilina 500mg',6500,10);
INSERT INTO productos(id_producto,codigo_barra,nombre_medicamento,precio_unitario,stock_actual)
VALUES (4,'7441001230104','Loratadina 10mg',1800,12);
INSERT INTO clientes(id_cliente,cedula,nombre,telefono,nodo_origen,sincronizado)
VALUES ('1001-SUC3','307890123','Ana Lucia Solano','8700-9988','SUC3',0);
INSERT INTO facturas(id_factura,id_cliente,fecha_emision,total,nodo_emisor,sincronizado)
VALUES (300001,'1001-SUC3',TIMESTAMP '2026-11-17 14:30:00',6500,'SUC3',0);
INSERT INTO detalle_factura(id_factura,id_producto,cantidad,subtotal,nodo_origen,id_detalle_origen)
VALUES (300001,3,1,6500,'SUC3',1);
COMMIT;
