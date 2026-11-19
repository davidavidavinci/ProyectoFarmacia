-- EJECUTAR EN FARMACIA_CENTRAL dentro de XEPDB1
-- Agregar también estas tablas al DDL común de los demás nodos antes de la entrega.
CREATE TABLE control_secuencia_sync (
    origen VARCHAR2(10) PRIMARY KEY,
    ultima_secuencia NUMBER DEFAULT 0 NOT NULL
);

CREATE TABLE paquetes_recibidos (
    id_paquete VARCHAR2(80) PRIMARY KEY,
    origen VARCHAR2(10) NOT NULL,
    secuencia NUMBER NOT NULL,
    hash_sha256 VARCHAR2(64) NOT NULL,
    fecha_aplicacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_paquete_origen_secuencia UNIQUE (origen, secuencia)
);

INSERT INTO control_secuencia_sync (origen, ultima_secuencia)
VALUES ('SUC3', 0);
COMMIT;
