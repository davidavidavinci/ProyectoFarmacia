
import json
import hashlib
from pathlib import Path

carpeta = Path("paquetes")

ruta_paquete = carpeta / "paquete_CENTRAL_0001.json"
ruta_sucursal = carpeta / "datos_suc3.json"


def leer_json(ruta):
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=4, ensure_ascii=False)


def validar_paquete(paquete):
    contenido = paquete["contenido"]

    datos = json.dumps(
        contenido,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")

    hash_calculado = hashlib.sha256(datos).hexdigest()

    return hash_calculado == paquete["sha256"]


def importar_paquete():

    if not ruta_paquete.exists():
        print("Error: no se encuentra el paquete de CENTRAL.")
        return

    try:
        paquete = leer_json(ruta_paquete)

        if not validar_paquete(paquete):
            print("Error: integridad del paquete incorrecta.")
            return

        contenido = paquete["contenido"]

        if contenido["origen"] != "CENTRAL":
            print("Error: origen incorrecto.")
            return

        if contenido["destino"] != "SUC3":
            print("Error: destino incorrecto.")
            return

        if ruta_sucursal.exists():
            sucursal = leer_json(ruta_sucursal)
        else:
            # Simular los datos originales de SUC3
            paquete_local = leer_json(
                carpeta / "paquete_SUC3_0001.json"
            )

            sucursal = {
                "ultima_secuencia_central": 0,
                "paquetes_recibidos": [],
                "productos": [],
                "clientes": paquete_local["contenido"]["clientes"]
            }

        id_paquete = contenido["id_paquete"]
        secuencia = contenido["secuencia"]

        if id_paquete in sucursal["paquetes_recibidos"]:
            print("Este paquete ya fue aplicado.")
            return

        if secuencia != sucursal["ultima_secuencia_central"] + 1:
            print("Error: paquete fuera de orden.")
            return

        # Actualizar productos por codigo de barras
        for producto in contenido["productos"]:

            encontrado = False

            for local in sucursal["productos"]:
                if local["codigo_barra"] == producto["codigo_barra"]:

                    local["nombre_medicamento"] = producto[
                        "nombre_medicamento"
                    ]

                    local["precio_unitario"] = producto[
                        "precio_unitario"
                    ]

                    encontrado = True
                    break

            if not encontrado:
                nuevo = producto.copy()
                nuevo["stock_actual"] = 0
                sucursal["productos"].append(nuevo)

        # Distribuir clientes sin duplicar cedulas
        for cliente in contenido["clientes"]:

            encontrado = False

            for local in sucursal["clientes"]:
                if local["cedula"] == cliente["cedula"]:
                    encontrado = True
                    break

            if not encontrado:
                sucursal["clientes"].append(cliente.copy())

        sucursal["ultima_secuencia_central"] = secuencia
        sucursal["paquetes_recibidos"].append(id_paquete)

        guardar_json(ruta_sucursal, sucursal)

        print("Paquete importado correctamente.")
        print("Productos:", len(sucursal["productos"]))
        print("Clientes:", len(sucursal["clientes"]))

    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Error al importar:", error)


importar_paquete()
