
import json
import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from conexion_oracle import conectar_oracle


carpeta = Path(__file__).resolve().parent / "paquetes_oracle"
carpeta.mkdir(exist_ok=True)


def convertir_registros(cursor):
    columnas = [
        columna[0].lower()
        for columna in cursor.description
    ]

    registros = []

    for fila in cursor.fetchall():
        registro = dict(zip(columnas, fila))

        for clave, valor in registro.items():
            if isinstance(valor, datetime):
                registro[clave] = valor.isoformat()

            elif isinstance(valor, Decimal):
                registro[clave] = float(valor)

        registros.append(registro)

    return registros


def generar_paquete():

    with conectar_oracle() as conexion:
        cursor = conexion.cursor()

        cursor.execute("SELECT id_nodo FROM config_nodo")
        nodo = cursor.fetchone()

        if nodo is None or nodo[0] != "SUC3":
            print("Error: esta base no corresponde a SUC3")
            return

        cursor.execute("""
            SELECT id_cliente, cedula, nombre,
                   telefono, nodo_origen
            FROM clientes
            WHERE sincronizado = 0
              AND nodo_origen = 'SUC3'
            ORDER BY id_cliente
        """)

        clientes = convertir_registros(cursor)

        cursor.execute("""
            SELECT id_factura, id_cliente,
                   fecha_emision, total, nodo_emisor
            FROM facturas
            WHERE sincronizado = 0
              AND nodo_emisor = 'SUC3'
            ORDER BY id_factura
        """)

        facturas = convertir_registros(cursor)

        cursor.execute("""
            SELECT d.id_detalle_origen,
                   d.id_factura,
                   d.id_producto,
                   d.cantidad,
                   d.subtotal
            FROM detalle_factura d
            INNER JOIN facturas f
                ON d.id_factura = f.id_factura
            WHERE f.sincronizado = 0
              AND f.nodo_emisor = 'SUC3'
            ORDER BY d.id_factura, d.id_detalle_origen
        """)

        detalles = convertir_registros(cursor)

        for factura in facturas:
            detalles_factura = [
                detalle for detalle in detalles
                if detalle["id_factura"] == factura["id_factura"]
            ]

            if not detalles_factura:
                print("Factura sin detalles:", factura["id_factura"])
                return

            suma = sum(
                Decimal(str(detalle["subtotal"]))
                for detalle in detalles_factura
            )

            total = Decimal(str(factura["total"]))

            if suma != total:
                print("Total incorrecto:", factura["id_factura"])
                return

        if not clientes and not facturas:
            print("No hay registros pendientes.")
            return

        contenido = {
            "id_paquete": "SUC3-0001",
            "origen": "SUC3",
            "destino": "CENTRAL",
            "secuencia": 1,
            "fecha_generacion": datetime.now().isoformat(),
            "clientes": clientes,
            "facturas": facturas,
            "detalles": detalles
        }

        datos = json.dumps(
            contenido,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":")
        ).encode("utf-8")

        hash_paquete = hashlib.sha256(datos).hexdigest()

        paquete = {
            "contenido": contenido,
            "sha256": hash_paquete
        }

        ruta = carpeta / "paquete_SUC3_0001.json"

        with open(ruta, "x", encoding="utf-8") as archivo:
            json.dump(
                paquete,
                archivo,
                indent=4,
                ensure_ascii=False
            )

        print("Paquete generado correctamente")
        print("Archivo:", ruta)
        print("Clientes:", len(clientes))
        print("Facturas:", len(facturas))
        print("Detalles:", len(detalles))


try:
    generar_paquete()

except FileExistsError:
    print("El paquete SUC3-0001 ya existe.")
    print("No fue sobrescrito.")

except Exception as error:
    print("Error:", error)
