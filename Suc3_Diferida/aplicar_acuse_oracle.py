import json
import hashlib
import hmac
from pathlib import Path
from getpass import getpass
from decimal import Decimal
from conexion_oracle import conectar_oracle


carpeta = Path(__file__).resolve().parent / "paquetes_oracle"

ruta_paquete = carpeta / "paquete_SUC3_0001.json"
ruta_acuse = carpeta / "acuse_SUC3_0001.json"


def leer_json(ruta):
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def convertir_bytes(datos):
    return json.dumps(
        datos,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")


def aplicar_acuse():

    if not ruta_paquete.exists():
        print("Error: no existe el paquete original.")
        return

    if not ruta_acuse.exists():
        print("Error: no existe el acuse de CENTRAL.")
        return

    paquete = leer_json(ruta_paquete)
    documento = leer_json(ruta_acuse)

    contenido = paquete["contenido"]
    acuse = documento["acuse"]

    # Verificar el paquete original
    hash_calculado = hashlib.sha256(
        convertir_bytes(contenido)
    ).hexdigest()

    if not hmac.compare_digest(
        hash_calculado, paquete["sha256"]
    ):
        print("Error: el paquete original fue modificado.")
        return

    # Comprobar los datos del acuse
    if acuse["id_paquete"] != contenido["id_paquete"]:
        print("Error: identificador incorrecto.")
        return

    if acuse["secuencia"] != contenido["secuencia"]:
        print("Error: secuencia incorrecta.")
        return

    if acuse["hash_paquete"] != hash_calculado:
        print("Error: hash del paquete incorrecto.")
        return

    if acuse["origen"] != "CENTRAL":
        print("Error: origen incorrecto.")
        return

    if acuse["destino"] != "SUC3":
        print("Error: destino incorrecto.")
        return

    if contenido["origen"] != "SUC3":
        print("Error: paquete de origen incorrecto.")
        return

    if contenido["destino"] != "CENTRAL":
        print("Error: destino del paquete incorrecto.")
        return

    if acuse["estado"] != "APLICADO":
        print("Error: CENTRAL no confirmó el paquete.")
        return

    # Comprobar la autenticidad mediante HMAC
    clave = getpass("Clave compartida del acuse: ")

    firma_calculada = hmac.new(
        clave.encode("utf-8"),
        convertir_bytes(acuse),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        firma_calculada, documento["firma_hmac"]
    ):
        print("Error: firma HMAC incorrecta.")
        return

    print("Acuse verificado correctamente.")

    # Actualizar los registros reales de Oracle SUC3
    with conectar_oracle() as conexion:
        cursor = conexion.cursor()

        try:
            cursor.execute("SELECT id_nodo FROM config_nodo")
            nodos = cursor.fetchall()

            if nodos != [("SUC3",)]:
                raise ValueError("La base no corresponde a SUC3.")

            clientes = contenido["clientes"]
            facturas = contenido["facturas"]

            # Verificar que los clientes originales existan
            for cliente in clientes:
                cursor.execute("""
                    SELECT cedula, nodo_origen
                    FROM clientes
                    WHERE id_cliente = :id
                """, id=cliente["id_cliente"])

                fila = cursor.fetchone()

                if fila is None or fila != (
                    cliente["cedula"], "SUC3"
                ):
                    raise ValueError(
                        "Cliente no coincide con el paquete."
                    )

            # Verificar las facturas originales
            for factura in facturas:
                cursor.execute("""
                    SELECT id_cliente, total, nodo_emisor
                    FROM facturas
                    WHERE id_factura = :id
                """, id=factura["id_factura"])

                fila = cursor.fetchone()

                if fila is None:
                    raise ValueError("Factura no encontrada.")

                if (
                    fila[0] != factura["id_cliente"]
                    or Decimal(str(fila[1])) !=
                       Decimal(str(factura["total"]))
                    or fila[2] != "SUC3"
                ):
                    raise ValueError(
                        "Factura no coincide con el paquete."
                    )

            # Confirmar clientes
            for cliente in clientes:
                cursor.execute("""
                    UPDATE clientes
                    SET sincronizado = 1
                    WHERE id_cliente = :id
                      AND nodo_origen = 'SUC3'
                """, id=cliente["id_cliente"])

            # Confirmar facturas
            for factura in facturas:
                cursor.execute("""
                    UPDATE facturas
                    SET sincronizado = 1
                    WHERE id_factura = :id
                      AND nodo_emisor = 'SUC3'
                """, id=factura["id_factura"])

            conexion.commit()

            print("Datos actualizados en Oracle SUC3.")
            print("Paquete confirmado:",
                  contenido["id_paquete"])
            print("Clientes:", len(clientes))
            print("Facturas:", len(facturas))

        except Exception:
            conexion.rollback()
            raise


try:
    aplicar_acuse()

except Exception as error:
    print("Error al procesar el acuse:", error)




