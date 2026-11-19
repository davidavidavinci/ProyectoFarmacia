"""Convierte un paquete SUC3->CENTRAL verificado en SQL para Oracle SQL Developer.
No requiere pip ni la biblioteca oracledb. Uso:
    py preparar_importacion.py paquete_SUC3_0001.json
El SQL resultante se ejecuta LOCALMENTE en FARMACIA_CENTRAL/XEPDB1.
"""
import hashlib
import hmac
import json
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path




def abortar(mensaje):
    raise ValueError(mensaje)




def monto(valor):
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        abortar(f"Monto invalido: {valor}")
    if not d.is_finite() or d < 0 or d.as_tuple().exponent < -2:
        abortar(f"Monto invalido: {valor}")
    return d




def validar(contenido):
    sec = contenido.get("secuencia")
    if type(sec) is not int or sec < 1:
        abortar("Secuencia invalida")
    if (contenido.get("origen"), contenido.get("destino")) != ("SUC3", "CENTRAL"):
        abortar("Origen o destino incorrecto")
    if contenido.get("id_paquete") != f"SUC3-{sec:04d}":
        abortar("ID de paquete no coincide con secuencia")
    for nombre in ("clientes", "facturas", "detalles"):
        if not isinstance(contenido.get(nombre), list):
            abortar(f"Falta lista {nombre}")
    clientes = contenido["clientes"]
    facturas = contenido["facturas"]
    detalles = contenido["detalles"]
    ids_cliente = {}
    cedulas = {}
    for c in clientes:
        if c["nodo_origen"] != "SUC3" or not c["id_cliente"] or not c["cedula"] or not c["nombre"]:
            abortar("Cliente invalido")
        if c["id_cliente"] in ids_cliente or c["cedula"] in cedulas:
            abortar("Cliente o cedula duplicados en paquete")
        ids_cliente[c["id_cliente"]] = c["cedula"]
        cedulas[c["cedula"]] = c["id_cliente"]
    ids_fact = {}
    for f in facturas:
        if f["nodo_emisor"] != "SUC3" or f["id_cliente"] not in ids_cliente:
            abortar("Factura con nodo o cliente incorrecto")
        if type(f["id_factura"]) is not int or f["id_factura"] in ids_fact:
            abortar("ID de factura invalido/duplicado")
        datetime.fromisoformat(f["fecha_emision"])
        monto(f["total"])
        ids_fact[f["id_factura"]] = f
    ids_det = set()
    totales = {x: Decimal('0') for x in ids_fact}
    for d in detalles:
        if d["id_factura"] not in ids_fact:
            abortar("Detalle sin factura")
        if type(d["id_detalle_origen"]) is not int or d["id_detalle_origen"] in ids_det:
            abortar("ID de detalle invalido/duplicado")
        if type(d["id_producto"]) is not int or type(d["cantidad"]) is not int or d["cantidad"] < 1:
            abortar("Producto o cantidad invalida")
        ids_det.add(d["id_detalle_origen"])
        totales[d["id_factura"]] += monto(d["subtotal"])
    for f in facturas:
        if totales[f["id_factura"]] != monto(f["total"]):
            abortar(f"Detalle incompleto/total distinto: factura {f['id_factura']}")
    if not clientes and not facturas:
        abortar("Paquete vacio")




def literal_sql(t):
    return "'" + t.replace("'", "''") + "'"




def main():
    if len(sys.argv) != 2:
        print('USO: py preparar_importacion.py "ruta\\paquete_SUC3_0001.json"')
        sys.exit(2)
    ruta = Path(sys.argv[1]).resolve()
    paquete = json.loads(ruta.read_text(encoding="utf-8"))
    contenido = paquete["contenido"]
    datos = json.dumps(contenido, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    hash_real = hashlib.sha256(datos.encode('utf-8')).hexdigest()
    if not isinstance(paquete.get('sha256'), str) or not hmac.compare_digest(hash_real, paquete['sha256']):
        abortar("SHA-256 NO coincide: no se genero SQL")
    validar(contenido)
    # Evitar que un literal SQL exceda limites; preservar caracteres Unicode.
    trozos = [datos[i:i+800] for i in range(0, len(datos), 800)]
    json_expr = ' ||\n        '.join('TO_CLOB('+literal_sql(p)+')' for p in trozos)
    pid, seq = contenido['id_paquete'], contenido['secuencia']
    sql = r'''-- SQL generado de un JSON validado con SHA-256 por preparar_importacion.py.
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


    v_contenido := __JSON_EXPR__;


    -- Bloqueo de control para que la secuencia no pueda aplicarse simultaneamente.
    SELECT ultima_secuencia INTO v_ultima
      FROM control_secuencia_sync WHERE origen='SUC3' FOR UPDATE;


    SELECT COUNT(*), MAX(hash_sha256) INTO v_veces, v_hash_antes
      FROM paquetes_recibidos WHERE id_paquete=__PACKAGE_ID__;


    IF v_veces > 0 THEN
       IF v_hash_antes <> __HASH__ THEN
         RAISE_APPLICATION_ERROR(-20502,'Mismo ID con hash diferente');
       END IF;
       v_resultado := 'REPETIDO';
    ELSE
       IF __SEQUENCE__ <> v_ultima + 1 THEN
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
         VALUES (__PACKAGE_ID__,'SUC3',__SEQUENCE__,__HASH__);
       UPDATE control_secuencia_sync SET ultima_secuencia=__SEQUENCE__
         WHERE origen='SUC3';
       v_resultado := 'APLICADO';
    END IF;


    COMMIT;
    DBMS_OUTPUT.PUT_LINE('Paquete: ' || v_resultado || '. ID: ' || __PACKAGE_ID__);
    DBMS_OUTPUT.PUT_LINE('SHA256 original verificado: ' || __HASH__);
EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    DBMS_OUTPUT.PUT_LINE('ERROR: ' || SQLERRM);
    RAISE;
END;
/
'''
    sql = sql.replace('__JSON_EXPR__', json_expr).replace('__PACKAGE_ID__', literal_sql(pid)).replace('__HASH__', literal_sql(hash_real)).replace('__SEQUENCE__', str(seq))
    destino = ruta.with_name('importar_'+pid.replace('-','_')+'.sql')
    if destino.exists():
        abortar(f"El SQL ya existe: {destino}. No se sobrescribio")
    destino.write_text(sql, encoding='utf-8')
    print(f"INTEGRIDAD OK | SHA-256: {hash_real}")
    print(f"Se genero: {destino}")
    print(f"Clientes: {len(contenido['clientes'])}; facturas: {len(contenido['facturas'])}; detalles: {len(contenido['detalles'])}")
    print('Abra el .sql en SQL Developer CENTRAL y ejecútelo con F5.')




if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print('NO SE GENERO EL SQL:', exc)
        sys.exit(1)




