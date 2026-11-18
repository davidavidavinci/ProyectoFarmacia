-- EJECUTAR COMO SYSTEM CONECTADO A XEPDB1, POR SEPARADO EN CENTRAL Y EN SUC3.
-- Sustituir la contrasena de ejemplo por una contrasena privada.
-- No ejecutar si FARMACIA ya existe; en tal caso usar GRANT solamente si faltan permisos.
CREATE USER FARMACIA IDENTIFIED BY "CAMBIAR_CLAVE" DEFAULT TABLESPACE USERS TEMPORARY TABLESPACE TEMP QUOTA 100M ON USERS;
GRANT CREATE SESSION, CREATE TABLE, CREATE PROCEDURE TO FARMACIA;
-- Privilegios adicionales para el modo conectado se coordinan con Persona 2.
