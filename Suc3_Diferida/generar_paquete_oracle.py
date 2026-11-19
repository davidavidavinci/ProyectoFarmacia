
from control_secuencias import guardar_paquete

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
            WHERE nodo_origen = 'SUC3'
            AND (
                sincronizado = 0
                OR id_cliente IN (
                    SELECT id_cliente
                    FROM facturas
                    WHERE sincronizado = 0
                        AND nodo_emisor = 'SUC3'
                )
            )
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

        
    def construir_contenido(secuencia):
        return {
            "id_paquete": f"SUC3-{secuencia:04d}",
            "origen": "SUC3",
            "destino": "CENTRAL",
            "secuencia": secuencia,
            "fecha_generacion": datetime.now().isoformat(),
            "clientes": clientes,
            "facturas": facturas,
            "detalles": detalles
        }

    guardar_paquete(
        origen="SUC3",
        carpeta=Path(__file__).resolve().parent / "paquetes_oracle",
        construir_contenido=construir_contenido
    )



try:
    generar_paquete()

except FileExistsError:
    print("Ya existe un paquete con esa secuencia.")
    print("No fue sobrescrito.")

except Exception as error:
    print("Error:", error)
