import hashlib
import hmac
import json
import re
import sys
from decimal import Decimal
from getpass import getpass
from pathlib import Path

from conexion_oracle import conectar_oracle

CARPETA = Path(__file__).resolve().parent / "paquetes_oracle"
PATRON = re.compile(r"acuse_SUC3_(\d+)\.json$")


def bytes_canonicos(datos):
    return json.dumps(
        datos, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def elegir_archivos():
    opciones = []
    for ruta_acuse in CARPETA.glob("acuse_SUC3_*.json"):
        coincidencia = PATRON.fullmatch(ruta_acuse.name)
        if coincidencia:
            numero = int(coincidencia.group(1))
            ruta_paquete = CARPETA / f"paquete_SUC3_{numero:04d}.json"
            if ruta_paquete.exists():
                opciones.append((numero, ruta_paquete, ruta_acuse))

    if len(sys.argv) > 1:
        try:
            numero_buscado = int(sys.argv[1])
        except ValueError:
            raise ValueError("Uso: python aplicar_acuse_oracle.py [numero]")
        for opcion in opciones:
            if opcion[0] == numero_buscado:
                return opcion
        raise ValueError("No hay acuse y paquete para ese numero.")

    if not opciones:
        raise ValueError("No hay pares paquete/acuse en paquetes_oracle.")

    # Por defecto, procesa el acuse mas reciente disponible.
    return max(opciones, key=lambda elemento: elemento[0])


def aplicar_acuse():
    numero, ruta_paquete, ruta_acuse = elegir_archivos()
    with ruta_paquete.open("r", encoding="utf-8") as archivo:
        paquete = json.load(archivo)
    with ruta_acuse.open("r", encoding="utf-8") as archivo:
        documento = json.load(archivo)

    contenido = paquete["contenido"]
    acuse = documento["acuse"]
    identificador = f"SUC3-{numero:04d}"
    hash_calculado = hashlib.sha256(bytes_canonicos(contenido)).hexdigest()

    if not hmac.compare_digest(hash_calculado, paquete["sha256"]):
        raise ValueError("El paquete original fue modificado.")

    if (contenido.get("id_paquete") != identificador
            or contenido.get("origen") != "SUC3"
            or contenido.get("destino") != "CENTRAL"
            or type(contenido.get("secuencia")) is not int
            or contenido["secuencia"] != numero):
        raise ValueError("Datos de origen del paquete incorrectos.")

    if (acuse.get("id_paquete") != identificador
            or acuse.get("origen") != "CENTRAL"
            or acuse.get("destino") != "SUC3"
            or type(acuse.get("secuencia")) is not int
            or acuse["secuencia"] != numero
            or acuse.get("estado") != "APLICADO"
            or not hmac.compare_digest(str(acuse.get("hash_paquete", "")), hash_calculado)):
        raise ValueError("El acuse no corresponde al paquete.")

    clave = getpass("Clave compartida del acuse: ")
    firma_calculada = hmac.new(
        clave.encode("utf-8"), bytes_canonicos(acuse), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(firma_calculada, str(documento.get("firma_hmac", ""))):
        raise ValueError("Firma HMAC incorrecta.")

    print("Acuse verificado:", identificador)
    with conectar_oracle() as conexion:
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT id_nodo FROM config_nodo")
            if cursor.fetchall() != [("SUC3",)]:
                raise ValueError("La base conectada no corresponde a SUC3.")

            clientes = contenido["clientes"]
            facturas = contenido["facturas"]

            for cliente in clientes:
                cursor.execute("""
                    SELECT cedula, nodo_origen
                    FROM clientes WHERE id_cliente = :id
                """, id=cliente["id_cliente"])
                fila = cursor.fetchone()
                if fila is None or fila != (cliente["cedula"], "SUC3"):
                    raise ValueError("Cliente diferente al paquete: " + str(cliente["id_cliente"]))

            for factura in facturas:
                cursor.execute("""
                    SELECT id_cliente, total, nodo_emisor
                    FROM facturas WHERE id_factura = :id
                """, id=factura["id_factura"])
                fila = cursor.fetchone()
                if (fila is None
                        or fila[0] != factura["id_cliente"]
                        or Decimal(str(fila[1])) != Decimal(str(factura["total"]))
                        or fila[2] != "SUC3"):
                    raise ValueError("Factura diferente al paquete: " + str(factura["id_factura"]))

            for cliente in clientes:
                cursor.execute("""
                    UPDATE clientes SET sincronizado = 1
                    WHERE id_cliente = :id AND nodo_origen = 'SUC3'
                """, id=cliente["id_cliente"])

            for factura in facturas:
                cursor.execute("""
                    UPDATE facturas SET sincronizado = 1
                    WHERE id_factura = :id AND nodo_emisor = 'SUC3'
                """, id=factura["id_factura"])

            conexion.commit()
            print("Confirmacion aplicada en Oracle SUC3:", identificador)
            print("Clientes:", len(clientes), "Facturas:", len(facturas))
        except Exception:
            conexion.rollback()
            raise


if __name__ == "__main__":
    try:
        aplicar_acuse()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print("ERROR:", error)
    except Exception as error:
        print("Error de Oracle:", error)
