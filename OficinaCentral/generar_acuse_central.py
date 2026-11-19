import json
import hashlib
import hmac
from getpass import getpass
from pathlib import Path
from datetime import datetime

carpeta = Path(__file__).resolve().parent

ruta_paquete = carpeta / "paquete_SUC3_0001.json"
ruta_acuse = carpeta / "acuse_SUC3_0001.json"


def convertir_bytes(datos):
    return json.dumps(
        datos,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")


def generar_acuse():
    if not ruta_paquete.exists():
        print("Error: no existe el paquete original.")
        return

    with open(ruta_paquete, "r", encoding="utf-8") as archivo:
        paquete = json.load(archivo)

    contenido = paquete["contenido"]

    hash_calculado = hashlib.sha256(
        convertir_bytes(contenido)
    ).hexdigest()

    if not hmac.compare_digest(
        hash_calculado, paquete["sha256"]
    ):
        print("Error: integridad del paquete incorrecta.")
        return

    print("Paquete:", contenido["id_paquete"])
    print("SHA-256:", hash_calculado)

    hash_oracle = input(
        "Pega el HASH_SHA256 registrado en Oracle: "
    ).strip().lower()

    if not hmac.compare_digest(hash_calculado, hash_oracle):
        print("Error: el hash no coincide con Oracle.")
        return

    if contenido["origen"] != "SUC3":
        print("Error: origen incorrecto.")
        return

    if contenido["destino"] != "CENTRAL":
        print("Error: destino incorrecto.")
        return

    clave = getpass("Clave compartida para firmar el acuse: ")

    acuse = {
        "id_paquete": contenido["id_paquete"],
        "origen": "CENTRAL",
        "destino": "SUC3",
        "secuencia": contenido["secuencia"],
        "estado": "APLICADO",
        "hash_paquete": hash_calculado,
        "fecha_acuse": datetime.now().isoformat()
    }

    firma = hmac.new(
        clave.encode("utf-8"),
        convertir_bytes(acuse),
        hashlib.sha256
    ).hexdigest()

    documento = {
        "acuse": acuse,
        "firma_hmac": firma
    }

    with open(ruta_acuse, "x", encoding="utf-8") as archivo:
        json.dump(
            documento,
            archivo,
            indent=4,
            ensure_ascii=False
        )

    print("Acuse generado correctamente.")
    print("Archivo:", ruta_acuse)


try:
    generar_acuse()
except FileExistsError:
    print("El acuse ya existe. No fue sobrescrito.")
except (OSError, ValueError, KeyError, TypeError) as error:
    print("Error:", error)



