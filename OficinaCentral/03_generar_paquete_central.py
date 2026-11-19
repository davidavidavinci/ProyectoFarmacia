
from control_secuencias import guardar_paquete

import csv
import json
import hashlib
import hmac
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from getpass import getpass


carpeta = Path(__file__).resolve().parent
carpeta_exportacion = carpeta / "exportacion"

ruta_productos = carpeta_exportacion / "productos.csv"
ruta_clientes = carpeta_exportacion / "clientes.csv"
ruta_salida = carpeta / "paquete_CENTRAL_0001.json"


def leer_csv(ruta, columnas):
    if not ruta.exists():
        raise FileNotFoundError(
            "No existe el archivo: " + str(ruta)
        )

    with open(ruta, "r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)

        encabezados = {
            columna.strip().upper()
            for columna in (lector.fieldnames or [])
        }

        if not set(columnas).issubset(encabezados):
            raise ValueError(
                "Columnas incorrectas en " + ruta.name
            )

        registros = []

        for fila in lector:
            registro = {
                clave.strip().lower(): valor
                for clave, valor in fila.items()
                if clave is not None
            }
            registros.append(registro)

        return registros


def convertir_bytes(datos):
    return json.dumps(
        datos,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")


def generar_paquete():

    productos_csv = leer_csv(
        ruta_productos,
        [
            "ID_PRODUCTO",
            "CODIGO_BARRA",
            "NOMBRE_MEDICAMENTO",
            "PRECIO_UNITARIO"
        ]
    )

    clientes_csv = leer_csv(
        ruta_clientes,
        [
            "ID_CLIENTE",
            "CEDULA",
            "NOMBRE",
            "TELEFONO",
            "NODO_ORIGEN"
        ]
    )

    productos = []
    codigos = set()

    for fila in productos_csv:
        codigo = fila["codigo_barra"].strip()

        if codigo in codigos:
            raise ValueError(
                "Codigo de barras duplicado: " + codigo
            )

        codigos.add(codigo)

        precio = Decimal(
            fila["precio_unitario"].strip()
        )

        if precio < 0:
            raise ValueError("Precio negativo.")

        productos.append({
            "id_producto": int(fila["id_producto"]),
            "codigo_barra": codigo,
            "nombre_medicamento":
                fila["nombre_medicamento"].strip(),
            "precio_unitario": format(precio, "f")
        })

    clientes = []
    cedulas = set()

    for fila in clientes_csv:
        cedula = fila["cedula"].strip()

        if cedula in cedulas:
            raise ValueError(
                "Cedula duplicada: " + cedula
            )

        cedulas.add(cedula)

        clientes.append({
            "id_cliente": fila["id_cliente"].strip(),
            "cedula": cedula,
            "nombre": fila["nombre"].strip(),
            "telefono": (fila["telefono"] or "").strip(),
            "nodo_origen": fila["nodo_origen"].strip()
        })

    if not productos:
        raise ValueError(
            "El catalogo no contiene productos."
        )

    
    def construir_contenido(secuencia):
        return {
            "id_paquete": f"CENTRAL-{secuencia:04d}",
            "origen": "CENTRAL",
            "destino": "SUC3",
            "secuencia": secuencia,
            "fecha_generacion": datetime.now().isoformat(),
            "productos": productos,
            "clientes": clientes
        }

    clave = getpass("Clave compartida CENTRAL-SUC3: ")

    guardar_paquete(
        origen="CENTRAL",
        carpeta=carpeta,
        construir_contenido=construir_contenido,
        clave=clave
    )



try:
    generar_paquete()

except FileExistsError:
    print("CENTRAL-0001 ya existe.")
    print("No se sobrescribio el paquete anterior.")

except Exception as error:
    print("Error al generar el paquete:", error)
