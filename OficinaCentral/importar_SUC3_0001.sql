-- SQL generado de un JSON validado con SHA-256 por preparar_importacion.py.
-- Ejecutar con F5 en SQL Developer, conectado como FARMACIA_CENTRAL/XEPDB1.
-- Necesita PKG_RECEPCION VALID y las tablas CONTROL_SECUENCIA_SYNC / PAQUETES_RECIBIDOS.
SET SERVEROUTPUT ON SIZE UNLIMITED
DECLARE
    v_contenido CLOB;
    v_ultima NUMBER;
    v_hash_antes VARCHAR2(64);
    v_veces NUMBER := 0;
    v_resultado VARCHAR2(20);
BEGIN
    IF USER <> 'FARMACIA_CENTRAL'
       OR SYS_CONTEXT('USERENV','CON_NAME') <> 'XEPDB1' THEN
       RAISE_APPLICATION_ERROR(-20501,'Conectese a FARMACIA_CENTRAL / XEPDB1');
    END IF;


    v_contenido := TO_CLOB('{"clientes":[{"cedula":"307890123","id_cliente":"1001-SUC3","nodo_origen":"SUC3","nombre":"Ana Lucia Solano","telefono":"8700-9988"}],"destino":"CENTRAL","detalles":[{"cantidad":1,"id_detalle_origen":1,"id_factura":300001,"id_producto":3,"subtotal":6500.0}],"facturas":[{"fecha_emision":"2026-11-17T14:30:00","id_cliente":"1001-SUC3","id_factura":300001,"nodo_emisor":"SUC3","total":6500.0}],"fecha_generacion":"2026-11-18T21:59:38.106504","id_paquete":"SUC3-0001","origen":"SUC3","secuencia":1}');


    -- Bloqueo de control para que la secuencia no pueda aplicarse simultaneamente.
    SELECT ultima_secuencia INTO v_ultima
      FROM control_secuencia_sync WHERE origen='SUC3' FOR UPDATE;


    SELECT COUNT(*), MAX(hash_sha256) INTO v_veces, v_hash_antes
      FROM paquetes_recibidos WHERE id_paquete='SUC3-0001';


    IF v_veces > 0 THEN
       IF v_hash_antes <> 'bc90648538ab417b63b6ab2e1b6447fed05450412921617bed70948475b390b0' THEN
         RAISE_APPLICATION_ERROR(-20502,'Mismo ID con hash diferente');
       END IF;
       v_resultado := 'REPETIDO';
    ELSE
       IF 1 <> v_ultima + 1 THEN
          RAISE_APPLICATION_ERROR(-20503,'Paquete fuera de orden. Ultima secuencia: ' || v_ultima);
       END IF;


       FOR cli IN (
           SELECT j.id_cliente, j.cedula, j.nombre, j.telefono, j.nodo_origen
           FROM JSON_TABLE(v_contenido, '$.clientes[*]'
             COLUMNS (
                id_cliente VARCHAR2(30) PATH '$.id_cliente',
                cedula VARCHAR2(20) PATH '$.cedula',
                nombre VARCHAR2(100) PATH '$.nombre',
                telefono VARCHAR2(20) PATH '$.telefono',
                nodo_origen VARCHAR2(10) PATH '$.nodo_origen'
             )) j
       ) LOOP
           pkg_recepcion.recibir_cliente(cli.id_cliente,cli.cedula,
                                          cli.nombre,cli.telefono,cli.nodo_origen);
       END LOOP;


       FOR fac IN (
           SELECT j.id_factura, c.cedula, j.fecha_emision, j.total, j.nodo_emisor
           FROM JSON_TABLE(v_contenido, '$.facturas[*]'
             COLUMNS (
                id_factura NUMBER PATH '$.id_factura',
                id_cliente VARCHAR2(30) PATH '$.id_cliente',
                fecha_emision VARCHAR2(40) PATH '$.fecha_emision',
                total NUMBER PATH '$.total',
                nodo_emisor VARCHAR2(10) PATH '$.nodo_emisor'
             )) j
           JOIN JSON_TABLE(v_contenido, '$.clientes[*]'
             COLUMNS (
                id_cliente VARCHAR2(30) PATH '$.id_cliente',
                cedula VARCHAR2(20) PATH '$.cedula'
             )) c ON c.id_cliente = j.id_cliente
       ) LOOP
           pkg_recepcion.recibir_factura(
               fac.id_factura, fac.cedula,
               TO_TIMESTAMP(REPLACE(SUBSTR(fac.fecha_emision,1,19),'T',' '),
                            'YYYY-MM-DD HH24:MI:SS'),
               fac.total, fac.nodo_emisor);
       END LOOP;


       FOR det IN (
           SELECT j.id_detalle_origen,j.id_factura,j.id_producto,j.cantidad,j.subtotal
           FROM JSON_TABLE(v_contenido, '$.detalles[*]'
             COLUMNS (
                id_detalle_origen NUMBER PATH '$.id_detalle_origen',
                id_factura NUMBER PATH '$.id_factura',
                id_producto NUMBER PATH '$.id_producto',
                cantidad NUMBER PATH '$.cantidad',
                subtotal NUMBER PATH '$.subtotal'
             )) j
       ) LOOP
           pkg_recepcion.recibir_detalle('SUC3',det.id_detalle_origen,
                            det.id_factura,det.id_producto,det.cantidad,det.subtotal);
       END LOOP;


       INSERT INTO paquetes_recibidos (id_paquete,origen,secuencia,hash_sha256)
         VALUES ('SUC3-0001','SUC3',1,'bc90648538ab417b63b6ab2e1b6447fed05450412921617bed70948475b390b0');
       UPDATE control_secuencia_sync SET ultima_secuencia=1
         WHERE origen='SUC3';
       v_resultado := 'APLICADO';
    END IF;


    COMMIT;
    DBMS_OUTPUT.PUT_LINE('Paquete: ' || v_resultado || '. ID: ' || 'SUC3-0001');
    DBMS_OUTPUT.PUT_LINE('SHA256 original verificado: ' || 'bc90648538ab417b63b6ab2e1b6447fed05450412921617bed70948475b390b0');
EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    DBMS_OUTPUT.PUT_LINE('ERROR: ' || SQLERRM);
    RAISE;
END;
/
