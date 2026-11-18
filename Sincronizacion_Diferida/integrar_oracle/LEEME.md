# Persona 3 — Primera integración con Oracle

Este paquete prepara **CENTRAL y SUC3**, usando el DDL compartido de Persona 2. Aun no automatiza el intercambio diferido completo.

1. Arrancar `farmacia-central` y `farmacia-suc3` en Docker. Comprobar que ambos están listos (`docker ps`, `docker logs`). Los puertos previstos son 1525 y 1526.
2. En SQL Developer, conectar `SYSTEM` a `localhost:1525/XEPDB1` para CENTRAL, y a `localhost:1526/XEPDB1` para SUC3. Crear el usuario `FARMACIA` por separado en cada uno con `02_preparar_cuentas.sql`. Cambiar contraseña. Si existe, NO ejecutar `CREATE USER` otra vez.
3. Conectar `FARMACIA` a ambas bases. Ejecutar `01_estructura_corregida_TODOS.sql` del ZIP de Persona 2 en cada una **solo si están vacías**.
4. Ejecutar `02a_datos_CENTRAL.sql` en CENTRAL y `03_central_recepcion.sql` en CENTRAL.
5. Ejecutar `03_semilla_SUC3.sql` **solo en SUC3**. No ejecutar tambien `02d_config_SUC3_PARA_PERSONA3.sql` porque ambas insertan la misma fila de `config_nodo`.
6. Ejecutar `04_control_paquetes.sql` en ambas bases (despues de acordarlo con Persona 1 por el requisito de esquema identico).
7. En PowerShell: `py -m pip install oracledb`.
8. Ejecutar `py 01_probar_conexiones.py`. Introducir usuario `FARMACIA` y clave en cada nodo.

**Avisos:** no borrar ni recrear tablas existentes para resolver un error. SUC3 debe seguir comunicandose con CENTRAL por archivos transportados manualmente, NO por Database Link. El script Python de verificacion puede conectarse individualmente a las dos bases **solo como herramienta local de desarrollo**. No prueba el modo diferido por si mismo.

**Pendiente**: generar paquetes directamente desde Oracle, importarlos transaccionalmente en CENTRAL, emitir/validar acuses, marcar registros confirmados, enviar catalogo y clientes de regreso. No afirmar que estos pasos estan completos antes de ejecutarlos y verificar los resultados.
