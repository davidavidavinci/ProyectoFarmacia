import hashlib
import hmac
import json
import re
import sys
from datetime import datetime
from getpass import getpass
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
PATRON = re.compile(r"paquete_SUC3_(\d+)\.json$")


def bytes_canonicos(datos):
    return json.dumps(
        datos, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def elegir_paquete():
    opciones = []
    for ruta in CARPETA.glob("paquete_SUC3_*.json"):
        coincidencia = PATRON.fullmatch(ruta.name)
        if coincidencia:
            numero = int(coincidencia.group(1))
            ruta_acuse = CARPETA / f"acuse_SUC3_{numero:04d}.json"
            if not ruta_acuse.exists():
                opciones.append((numero, ruta, ruta_acuse))

    if len(sys.argv) > 1:
        try:
            numero_buscado = int(sys.argv[1])
        except ValueError:
            raise ValueError("Uso: py generar_acuse_central.py [numero]")
        for opcion in opciones:
            if opcion[0] == numero_buscado:
                return opcion
        raise ValueError("No existe un paquete pendiente con ese numero.")

    if not opciones:
        raise ValueError("No hay paquetes SUC3 pendientes de acuse en esta carpeta.")

    # Atender primero el paquete mas antiguo sin acuse.
    return min(opciones, key=lambda elemento: elemento[0])


def generar_acuse():
    numero, ruta_paquete, ruta_acuse = elegir_paquete()
    with ruta_paquete.open("r", encoding="utf-8") as archivo:
        paquete = json.load(archivo)

    contenido = paquete["contenido"]
    identificador = f"SUC3-{numero:04d}"

    if (contenido.get("id_paquete") != identificador
            or contenido.get("origen") != "SUC3"
            or contenido.get("destino") != "CENTRAL"
            or type(contenido.get("secuencia")) is not int
            or contenido["secuencia"] != numero):
        raise ValueError("Identidad u origen del paquete incorrectos.")

    hash_calculado = hashlib.sha256(bytes_canonicos(contenido)).hexdigest()
    if not hmac.compare_digest(hash_calculado, paquete["sha256"]):
        raise ValueError("El paquete no supera la validacion SHA-256.")

    print("Paquete encontrado:", ruta_paquete.name)
    print("ID:", identificador)
    print("SHA-256:", hash_calculado)
    print("Comprueba en SQL Developer que el paquete fue APLICADO.")
    print("Consulta: SELECT hash_sha256 FROM paquetes_recibidos "
          f"WHERE id_paquete = '{identificador}';")
    hash_oracle = input("Pega el HASH_SHA256 registrado en Oracle CENTRAL: ").strip().lower()
    if not hmac.compare_digest(hash_oracle, hash_calculado):
        raise ValueError("El hash de Oracle no coincide. No se genera acuse.")

    confirmacion = input("¿Confirmaste que la importacion termino con COMMIT? (SI): ").strip().upper()
    if confirmacion != "SI":
        raise ValueError("No se genero el acuse sin confirmacion.")

    clave = getpass("Clave compartida para firmar el acuse: ")
    
    acuse = {
        "id_paquete": identificador,
        "origen": "CENTRAL",
        "destino": "SUC3",
        "secuencia": numero,
        "estado": "APLICADO",
        "hash_paquete": hash_calculado,
        "fecha_acuse": datetime.now().isoformat(),
    }
    firma = hmac.new(clave.encode("utf-8"), bytes_canonicos(acuse), hashlib.sha256).hexdigest()
    documento = {"acuse": acuse, "firma_hmac": firma}

    with ruta_acuse.open("x", encoding="utf-8") as archivo:
        json.dump(documento, archivo, ensure_ascii=False, indent=4)

    print("Acuse generado:", ruta_acuse.name)
    print("Envialo por correo a SUC3 / paquetes_oracle")


if __name__ == "__main__":
    try:
        generar_acuse()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print("ERROR:", error)
