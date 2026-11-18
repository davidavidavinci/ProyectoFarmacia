
import json
import hashlib
from pathlib import Path

ruta = Path("paquetes") / "paquete_SUC3_0001.json"

with open(ruta, "r", encoding="utf-8") as archivo:
    paquete = json.load(archivo)

contenido = paquete["contenido"]
hash_recibido = paquete["sha256"]

datos = json.dumps(
    contenido,
    sort_keys=True,
    ensure_ascii=False,
    separators=(",", ":")
).encode("utf-8")

hash_calculado = hashlib.sha256(datos).hexdigest()

if hash_recibido == hash_calculado:
    print("Paquete valido: integridad confirmada")
else:
    print("Error: el paquete fue modificado")
