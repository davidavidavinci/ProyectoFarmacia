-- SOLO CENTRAL, despues del DDL. En instalacion nueva.
INSERT INTO config_nodo VALUES ('CENTRAL');
INSERT INTO catalogo_nodos VALUES ('CENTRAL','Oficina Central - San Jose','CONECTADO',NULL);
INSERT INTO catalogo_nodos VALUES ('SUC1','Farmacia Sucursal 1','CONECTADO',NULL);
INSERT INTO catalogo_nodos VALUES ('SUC2','Farmacia Sucursal 2','CONECTADO',NULL);
INSERT INTO catalogo_nodos VALUES ('SUC3','Farmacia Sucursal 3','DIFERIDO',NULL);
INSERT INTO productos (codigo_barra,nombre_medicamento,precio_unitario,stock_actual)
 VALUES ('7441001230101','Acetaminofen 500mg',2500,500);
INSERT INTO productos (codigo_barra,nombre_medicamento,precio_unitario,stock_actual)
 VALUES ('7441001230102','Ibuprofeno 400mg',3200,300);
INSERT INTO productos (codigo_barra,nombre_medicamento,precio_unitario,stock_actual)
 VALUES ('7441001230103','Amoxicilina 500mg',6500,150);
INSERT INTO productos (codigo_barra,nombre_medicamento,precio_unitario,stock_actual)
 VALUES ('7441001230104','Loratadina 10mg',1800,400);
COMMIT;
