-- SCRIPT COMUN: aplicar en CENTRAL y SUC3 (y despues Persona 1 puede sumarlo al DDL de todos).
-- EJECUTAR UNA VEZ POR BASE DE DATOS Y SOLO DESPUES DEL DDL COMUN.
CREATE TABLE control_paquetes_diferidos (
 id_paquete VARCHAR2(60) PRIMARY KEY,
 origen VARCHAR2(10) NOT NULL,
 destino VARCHAR2(10) NOT NULL,
 secuencia NUMBER NOT NULL,
 hash_contenido VARCHAR2(64) NOT NULL,
 estado VARCHAR2(20) NOT NULL CHECK (estado IN ('GENERADO','APLICADO','CONFIRMADO')),
 fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
 CONSTRAINT uq_paquete_diferido_sec UNIQUE(origen,destino,secuencia)
);
COMMIT;
