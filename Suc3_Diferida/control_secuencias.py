
import hashlib
import hmac
import json
import re
import sqlite3
from pathlib import Path


def convertir_bytes(datos):
    return json.dumps(
        datos,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")


def guardar_paquete(origen, carpeta, construir_contenido,
                    clave=None):

    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)

    ruta_control = carpeta / "control_envios.sqlite3"

    conexion = sqlite3.connect(ruta_control)

    try:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS envios (
                origen TEXT NOT NULL,
                secuencia INTEGER NOT NULL,
                id_paquete TEXT NOT NULL,
                hash_sha256 TEXT NOT NULL,
                PRIMARY KEY (origen, secuencia)
            )
        """)

        conexion.commit()
        conexion.execute("BEGIN IMMEDIATE")

        fila = conexion.execute("""
            SELECT COALESCE(MAX(secuencia), 0)
            FROM envios
            WHERE origen = ?
        """, (origen,)).fetchone()

        ultima_secuencia = fila[0]

        # Reconocer también los paquetes 0001
        # que generamos antes de crear SQLite.
        patron = re.compile(
            rf"paquete_{re.escape(origen)}_(\d+)\.json"
        )

        for archivo in carpeta.glob("paquete_*.json"):
            coincidencia = patron.fullmatch(archivo.name)

            if coincidencia:
                numero = int(coincidencia.group(1))
                ultima_secuencia = max(
                    ultima_secuencia, numero
                )

        secuencia = ultima_secuencia + 1

        contenido = construir_contenido(secuencia)

        identificador = f"{origen}-{secuencia:04d}"

        if contenido["id_paquete"] != identificador:
            raise ValueError("Identificador incorrecto.")

        if contenido["secuencia"] != secuencia:
            raise ValueError("Secuencia incorrecta.")

        if contenido["origen"] != origen:
            raise ValueError("Origen incorrecto.")

        datos = convertir_bytes(contenido)
        hash_paquete = hashlib.sha256(datos).hexdigest()

        paquete = {
            "contenido": contenido,
            "sha256": hash_paquete
        }

        if clave is not None:
            paquete["firma_hmac"] = hmac.new(
                clave.encode("utf-8"),
                datos,
                hashlib.sha256
            ).hexdigest()

        ruta_salida = (
            carpeta /
            f"paquete_{origen}_{secuencia:04d}.json"
        )

        # Crear sin sobrescribir paquetes anteriores.
        with open(ruta_salida, "x", encoding="utf-8") as archivo:
            json.dump(
                paquete,
                archivo,
                indent=4,
                ensure_ascii=False
            )

        conexion.execute("""
            INSERT INTO envios (
                origen, secuencia, id_paquete, hash_sha256
            )
            VALUES (?, ?, ?, ?)
        """, (
            origen, secuencia,
            identificador, hash_paquete
        ))

        conexion.commit()

        print("Paquete generado:", identificador)
        print("Secuencia:", secuencia)
        print("SHA-256:", hash_paquete)
        print("Archivo:", ruta_salida)

        return ruta_salida

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()
