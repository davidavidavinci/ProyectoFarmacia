
import json
import hashlib
from datetime import datetime
from pathlib import Path

carpeta = Path("paquetes")
carpeta.mkdir(exist_ok=True)

clientes = [
    {
        "id_cliente": "1001-SUC3",
        "cedula": "307890123",
        "nombre": "Ana Lucia Solano",
        "telefono": "8700-9988",
        "nodo_origen": "SUC3"
    }
]

facturas = [
    {
        "id_factura": 300001,
        "id_cliente": "1001-SUC3",
        "fecha_emision": "2026-11-17T14:30:00",
        "total": 6500,
        "nodo_emisor": "SUC3"
    }
]

detalles = [
    {
        "id_detalle_origen": 1,
        "id_factura": 300001,
        "id_producto": 3,
        "cantidad": 1,
        "subtotal": 6500
    }
]

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

with open(ruta, "w", encoding="utf-8") as archivo:
    json.dump(paquete, archivo, indent=4, ensure_ascii=False)

print("Paquete generado correctamente")
print("Archivo:", ruta)
print("SHA-256:", hash_paquete)
