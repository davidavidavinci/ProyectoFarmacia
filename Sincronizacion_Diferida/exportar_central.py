
import json
import hashlib
from datetime import datetime
from pathlib import Path

carpeta = Path("paquetes")
carpeta.mkdir(exist_ok=True)

ruta_central = carpeta / "datos_central.json"
ruta_salida = carpeta / "paquete_CENTRAL_0001.json"

if not ruta_central.exists():
    print("Error: primero debes aplicar el paquete de SUC3.")

else:
    with open(ruta_central, "r", encoding="utf-8") as archivo:
        central = json.load(archivo)

    # Catálogo oficial de prueba
    productos = [
        {
            "id_producto": 1,
            "codigo_barra": "7441001230101",
            "nombre_medicamento": "Acetaminofen 500mg",
            "precio_unitario": 2500
        },
        {
            "id_producto": 2,
            "codigo_barra": "7441001230102",
            "nombre_medicamento": "Ibuprofeno 400mg",
            "precio_unitario": 3200
        },
        {
            "id_producto": 3,
            "codigo_barra": "7441001230103",
            "nombre_medicamento": "Amoxicilina 500mg",
            "precio_unitario": 6500
        },
        {
            "id_producto": 4,
            "codigo_barra": "7441001230104",
            "nombre_medicamento": "Loratadina 10mg",
            "precio_unitario": 1800
        }
    ]

    contenido = {
        "id_paquete": "CENTRAL-0001",
        "origen": "CENTRAL",
        "destino": "SUC3",
        "secuencia": 1,
        "fecha_generacion": datetime.now().isoformat(),
        "productos": productos,
        "clientes": central["clientes"]
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

    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        json.dump(paquete, archivo, indent=4, ensure_ascii=False)

    print("Paquete de CENTRAL generado correctamente.")
    print("Archivo:", ruta_salida)
    print("Productos:", len(productos))
    print("Clientes:", len(central["clientes"]))
    print("SHA-256:", hash_paquete)
