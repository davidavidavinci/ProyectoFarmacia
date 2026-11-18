"""Importa un paquete SUC3 -> CENTRAL a Oracle local; nunca conecta a SUC3.
Uso: py 02_importar_central_oracle.py "C:\\ruta\\paquete_SUC3_0001.json"
Requiere: py -m pip install oracledb
"""
import hashlib
import hmac
import json
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from getpass import getpass
from pathlib import Path

import oracledb


def canonical(contenido):
    return json.dumps(contenido, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def fail(mensaje):
    raise ValueError(mensaje)


def cargar_paquete(ruta):
    with ruta.open(encoding="utf-8") as archivo:
        paquete = json.load(archivo)
    contenido, recibido = paquete["contenido"], paquete["sha256"]
    esperado = hashlib.sha256(canonical(contenido)).hexdigest()
    if not isinstance(recibido, str) or not hmac.compare_digest(esperado, recibido):
        fail("Hash SHA-256 incorrecto: archivo alterado o incompleto")
    if contenido.get("origen") != "SUC3" or contenido.get("destino") != "CENTRAL":
        fail("El paquete no es SUC3 -> CENTRAL")
    seq = contenido.get("secuencia")
    if type(seq) is not int or seq < 1:
        fail("Secuencia invalida")
    if contenido.get("id_paquete") != f"SUC3-{seq:04d}":
        fail("ID del paquete no coincide con la secuencia")
    for nombre in ("clientes", "facturas", "detalles"):
        if not isinstance(contenido.get(nombre), list):
            fail(f"Lista {nombre} faltante")
    return contenido, esperado


def importe(valor):
    try:
        monto = Decimal(str(valor))
        if not monto.is_finite() or monto < 0 or monto.as_tuple().exponent < -2:
            fail("Monto monetario no valido")
        return monto
    except (InvalidOperation, TypeError):
        fail("Monto monetario incorrecto")


def comprobar_datos(c):
    clientes = c["clientes"]
    facturas = c["facturas"]
    detalles = c["detalles"]
    if not clientes and not facturas:
        fail("Paquete sin clientes ni facturas")
    cedulas = {}
    ids_clientes = set()
    for cli in clientes:
        if cli["nodo_origen"] != "SUC3":
            fail("Cliente con origen ajeno a SUC3")
        if cli["id_cliente"] in ids_clientes:
            fail("ID de cliente repetido en paquete")
        ids_clientes.add(cli["id_cliente"])
        if cli["cedula"] in cedulas and cedulas[cli["cedula"]] != cli["id_cliente"]:
            fail("Cedula duplicada en paquete")
        cedulas[cli["cedula"]] = cli["id_cliente"]

    ids_facturas = set()
    for f in facturas:
        if f["nodo_emisor"] != "SUC3":
            fail("Factura ajena a SUC3")
        if f["id_cliente"] not in ids_clientes:
            fail("Factura sin cliente en el paquete")
        if f["id_factura"] in ids_facturas:
            fail("Factura repetida en el paquete")
        ids_facturas.add(f["id_factura"])
        datetime.fromisoformat(f["fecha_emision"])
        importe(f["total"])

    ids_detalles = set()
    sumas = {i: Decimal("0") for i in ids_facturas}
    for d in detalles:
        if d["id_factura"] not in ids_facturas:
            fail("Detalle sin factura correspondiente")
        if d["id_detalle_origen"] in ids_detalles:
            fail("Detalle original duplicado")
        ids_detalles.add(d["id_detalle_origen"])
        if type(d["cantidad"]) is not int or d["cantidad"] <= 0:
            fail("Cantidad invalida")
        sumas[d["id_factura"]] += importe(d["subtotal"])
    for f in facturas:
        if sumas[f["id_factura"]] != importe(f["total"]):
            fail(f"Factura {f['id_factura']} sin detalles completos o total incorrecto")


def aplicar(contenido, hash_paquete, clave):
    with oracledb.connect(user="FARMACIA_CENTRAL", password=clave,
                          host="localhost", port=1521, service_name="XEPDB1") as con:
        try:
            with con.cursor() as cur:
                cur.execute("SELECT USER, SYS_CONTEXT('USERENV','CON_NAME') FROM dual")
                usuario, contenedor = cur.fetchone()
                if usuario != "FARMACIA_CENTRAL" or contenedor != "XEPDB1":
                    fail("Conexion no corresponde a FARMACIA_CENTRAL / XEPDB1")

                # Serializa importaciones del origen para evitar paquetes fuera de orden.
                cur.execute("SELECT ultima_secuencia FROM control_secuencia_sync "
                            "WHERE origen = 'SUC3' FOR UPDATE")
                fila = cur.fetchone()
                if fila is None:
                    fail("Falta el control de secuencia SUC3. Ejecuta 01_control_diferido.sql")
                ultima = int(fila[0])
                seq = contenido["secuencia"]
                cur.execute("SELECT hash_sha256 FROM paquetes_recibidos WHERE id_paquete=:id",
                            {"id": contenido["id_paquete"]})
                previo = cur.fetchone()
                if previo:
                    if previo[0] != hash_paquete:
                        fail("Mismo ID de paquete con contenido diferente")
                    con.rollback()
                    return "REPETIDO"
                if seq != ultima + 1:
                    fail(f"Fuera de orden: ultima aplicada {ultima}, recibida {seq}")

                # Clientes primero, luego facturas y finalmente detalles.
                for cli in contenido["clientes"]:
                    cur.callproc("pkg_recepcion.recibir_cliente", [
                        cli["id_cliente"], cli["cedula"], cli["nombre"],
                        cli.get("telefono"), cli["nodo_origen"]])
                cedulas = {c["id_cliente"]: c["cedula"] for c in contenido["clientes"]}
                for f in contenido["facturas"]:
                    cur.callproc("pkg_recepcion.recibir_factura", [
                        f["id_factura"], cedulas[f["id_cliente"]],
                        datetime.fromisoformat(f["fecha_emision"]),
                        importe(f["total"]), f["nodo_emisor"]])
                for d in contenido["detalles"]:
                    cur.callproc("pkg_recepcion.recibir_detalle", [
                        "SUC3", d["id_detalle_origen"], d["id_factura"],
                        d["id_producto"], d["cantidad"], importe(d["subtotal"])])
                cur.execute("INSERT INTO paquetes_recibidos "
                            "(id_paquete,origen,secuencia,hash_sha256) "
                            "VALUES (:id,'SUC3',:seq,:sha)",
                            {"id": contenido["id_paquete"], "seq": seq, "sha": hash_paquete})
                cur.execute("UPDATE control_secuencia_sync SET ultima_secuencia=:seq "
                            "WHERE origen='SUC3'", {"seq": seq})
            con.commit()
            return "APLICADO"
        except Exception:
            con.rollback()
            raise


def main():
    if len(sys.argv) != 2:
        print('Uso: py 02_importar_central_oracle.py "ruta_del_paquete.json"')
        return
    ruta = Path(sys.argv[1]).resolve()
    try:
        contenido, sha = cargar_paquete(ruta)
        comprobar_datos(contenido)
        clave = getpass("Contrasena local FARMACIA_CENTRAL: ")
        estado = aplicar(contenido, sha, clave)
        acuse = {
            "id_paquete": contenido["id_paquete"],
            "origen": "CENTRAL", "destino": "SUC3", "estado": "APLICADO",
            "secuencia": contenido["secuencia"], "sha256_paquete": sha
        }
        # El acuse se crea solo DESPUES del COMMIT exitoso.
        destino = ruta.with_name(f"acuse_{contenido['id_paquete']}.json")
        with destino.open("w", encoding="utf-8") as archivo:
            json.dump(acuse, archivo, ensure_ascii=False, indent=4)
        print(f"Paquete: {estado}. Acuse creado en: {destino}")
    except (OSError, ValueError, KeyError, TypeError, oracledb.Error) as exc:
        print("No se aplico el paquete:", exc)


if __name__ == "__main__":
    main()
