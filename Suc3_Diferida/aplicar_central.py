
import json
import hashlib
from pathlib import Path

carpeta = Path("paquetes")
carpeta.mkdir(exist_ok=True)

ruta_paquete = carpeta / "paquete_SUC3_0001.json"
ruta_central = carpeta / "datos_central.json"
ruta_acuse = carpeta / "acuse_SUC3_0001.json"


def guardar_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=4, ensure_ascii=False)


def leer_json(ruta):
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def validar_integridad(paquete):
    contenido = paquete["contenido"]

    datos = json.dumps(
        contenido,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")

    hash_calculado = hashlib.sha256(datos).hexdigest()

    return hash_calculado == paquete["sha256"]


def aplicar_paquete():
    if not ruta_paquete.exists():
        print("Error: no existe el paquete.")
        return

    try:
        paquete = leer_json(ruta_paquete)

        if not validar_integridad(paquete):
            print("Error: el paquete fue modificado.")
            return

        contenido = paquete["contenido"]

        if contenido["origen"] != "SUC3":
            print("Error: origen incorrecto.")
            return

        if contenido["destino"] != "CENTRAL":
            print("Error: destino incorrecto.")
            return

        if ruta_central.exists():
            central = leer_json(ruta_central)
        else:
            central = {
                "ultima_secuencia": 0,
                "paquetes_aplicados": [],
                "clientes": [],
                "facturas": [],
                "detalles": []
            }

        id_paquete = contenido["id_paquete"]
        secuencia = contenido["secuencia"]

        
        if id_paquete in central["paquetes_aplicados"]:
            print("El paquete ya fue aplicado.")

            guardar_json(ruta_acuse, {
                "id_paquete": id_paquete,
                "origen": "CENTRAL",
                "destino": "SUC3",
                "estado": "APLICADO",
                "secuencia": secuencia,
                "mensaje": "Paquete recibido anteriormente"
            })
            return


        if secuencia != central["ultima_secuencia"] + 1:
            print("Error: paquete fuera de orden.")
            return

        ids_clientes = {
            c["id_cliente"] for c in central["clientes"]
        }

        ids_facturas = {
            f["id_factura"] for f in central["facturas"]
        }

        ids_detalles = {
            (d["nodo_origen"], d["id_detalle_origen"])
            for d in central["detalles"]
        }

        for cliente in contenido["clientes"]:
            if cliente["id_cliente"] not in ids_clientes:
                central["clientes"].append(cliente)

        for factura in contenido["facturas"]:
            if factura["id_factura"] not in ids_facturas:
                central["facturas"].append(factura)

        for detalle in contenido["detalles"]:
            clave = (
                contenido["origen"],
                detalle["id_detalle_origen"]
            )

            if clave not in ids_detalles:
                nuevo_detalle = detalle.copy()
                nuevo_detalle["nodo_origen"] = contenido["origen"]
                central["detalles"].append(nuevo_detalle)

        central["ultima_secuencia"] = secuencia
        central["paquetes_aplicados"].append(id_paquete)

        guardar_json(ruta_central, central)

        guardar_json(ruta_acuse, {
            "id_paquete": id_paquete,
            "origen": "CENTRAL",
            "destino": "SUC3",
            "estado": "APLICADO",
            "secuencia": secuencia
        })

        print("Paquete aplicado correctamente.")
        print("Acuse generado:", ruta_acuse)

    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Error al procesar el paquete:", error)


aplicar_paquete()
