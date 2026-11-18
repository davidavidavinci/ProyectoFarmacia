
import json
from pathlib import Path

carpeta = Path("paquetes")

ruta_paquete = carpeta / "paquete_SUC3_0001.json"
ruta_acuse = carpeta / "acuse_SUC3_0001.json"
ruta_estado = carpeta / "estado_suc3.json"


def leer_json(ruta):
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=4, ensure_ascii=False)


def aplicar_acuse():
    if not ruta_paquete.exists():
        print("Error: no existe el paquete original.")
        return

    if not ruta_acuse.exists():
        print("Error: no ha llegado el acuse.")
        return

    try:
        paquete = leer_json(ruta_paquete)
        acuse = leer_json(ruta_acuse)
        contenido = paquete["contenido"]

        # Comprobar que el acuse corresponde al paquete
        if acuse.get("id_paquete") != contenido["id_paquete"]:
            print("Error: identificador de paquete incorrecto.")
            return

        if acuse.get("secuencia") != contenido["secuencia"]:
            print("Error: secuencia incorrecta.")
            return

        if acuse.get("origen") != "CENTRAL":
            print("Error: origen del acuse incorrecto.")
            return

        if acuse.get("destino") != "SUC3":
            print("Error: destino del acuse incorrecto.")
            return

        if acuse.get("estado") != "APLICADO":
            print("El paquete no fue confirmado.")
            return

        # Cargar el estado local de las confirmaciones
        if ruta_estado.exists():
            estado = leer_json(ruta_estado)
        else:
            estado = {
                "paquetes_confirmados": [],
                "clientes_confirmados": [],
                "facturas_confirmadas": []
            }

        id_paquete = contenido["id_paquete"]

        if id_paquete in estado["paquetes_confirmados"]:
            print("Este acuse ya fue procesado.")
            return

        for cliente in contenido["clientes"]:
            identificador = cliente["id_cliente"]

            if identificador not in estado["clientes_confirmados"]:
                estado["clientes_confirmados"].append(identificador)

        for factura in contenido["facturas"]:
            identificador = factura["id_factura"]

            if identificador not in estado["facturas_confirmadas"]:
                estado["facturas_confirmadas"].append(identificador)

        estado["paquetes_confirmados"].append(id_paquete)

        guardar_json(ruta_estado, estado)

        print("Acuse procesado correctamente.")
        print("Paquete confirmado:", id_paquete)
        print("Clientes confirmados:",
              len(contenido["clientes"]))
        print("Facturas confirmadas:",
              len(contenido["facturas"]))

    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Error al procesar el acuse:", error)


aplicar_acuse()
