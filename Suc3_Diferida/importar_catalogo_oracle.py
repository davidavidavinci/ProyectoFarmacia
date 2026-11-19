
import json
import hashlib
import hmac
from pathlib import Path
from decimal import Decimal, InvalidOperation
from getpass import getpass

from conexion_oracle import conectar_oracle


carpeta = Path(__file__).resolve().parent / "paquetes_oracle"
ruta = carpeta / "paquete_CENTRAL_0001.json"


def convertir_bytes(datos):
    return json.dumps(
        datos,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":")
    ).encode("utf-8")


def verificar_paquete(paquete):
    contenido = paquete["contenido"]

    if contenido["origen"] != "CENTRAL":
        raise ValueError("El origen no es CENTRAL.")

    if contenido["destino"] != "SUC3":
        raise ValueError("El destino no es SUC3.")

    secuencia = contenido["secuencia"]

    if type(secuencia) is not int or secuencia < 1:
        raise ValueError("Secuencia incorrecta.")

    if contenido["id_paquete"] != f"CENTRAL-{secuencia:04d}":
        raise ValueError("Identificador del paquete incorrecto.")

    if not isinstance(contenido["productos"], list):
        raise ValueError("La lista de productos es incorrecta.")

    if not isinstance(contenido["clientes"], list):
        raise ValueError("La lista de clientes es incorrecta.")

    datos = convertir_bytes(contenido)

    hash_calculado = hashlib.sha256(datos).hexdigest()

    if not hmac.compare_digest(
        hash_calculado, paquete["sha256"]
    ):
        raise ValueError("El hash SHA-256 no coincide.")

    clave = getpass("Clave compartida CENTRAL-SUC3: ")

    firma = hmac.new(
        clave.encode("utf-8"),
        datos,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        firma, paquete["firma_hmac"]
    ):
        raise ValueError("Firma HMAC incorrecta.")

    print("Integridad y firma verificadas.")

    return contenido, hash_calculado


def validar_registros(contenido):
    codigos = set()
    identificadores = set()

    for producto in contenido["productos"]:
        codigo = str(producto["codigo_barra"]).strip()
        identificador = producto["id_producto"]

        if not codigo or codigo in codigos:
            raise ValueError("Codigo de barras vacio o repetido.")

        if type(identificador) is not int or identificador < 1:
            raise ValueError("ID de producto incorrecto.")

        if identificador in identificadores:
            raise ValueError("ID de producto repetido.")

        nombre = str(producto["nombre_medicamento"]).strip()

        if not nombre or len(nombre) > 100:
            raise ValueError("Nombre de producto incorrecto.")

        try:
            precio = Decimal(str(producto["precio_unitario"]))
        except InvalidOperation:
            raise ValueError("Precio incorrecto.")

        if not precio.is_finite() or precio < 0:
            raise ValueError("Precio invalido.")

        if precio.as_tuple().exponent < -2:
            raise ValueError("Precio con demasiados decimales.")

        if len(codigo) > 50 or precio >= 100000000:
            raise ValueError("Producto fuera de los limites.")

        codigos.add(codigo)
        identificadores.add(identificador)

    cedulas = set()
    ids_clientes = set()

    for cliente in contenido["clientes"]:
        cedula = str(cliente["cedula"]).strip()
        identificador = str(cliente["id_cliente"]).strip()
        nombre = str(cliente["nombre"]).strip()

        if not cedula or cedula in cedulas:
            raise ValueError("Cedula vacia o repetida.")

        if not identificador or identificador in ids_clientes:
            raise ValueError("ID de cliente vacio o repetido.")

        if not nombre or len(nombre) > 100:
            raise ValueError("Nombre de cliente incorrecto.")

        if len(cedula) > 20 or len(identificador) > 30:
            raise ValueError("Cliente fuera de los limites.")

        cedulas.add(cedula)
        ids_clientes.add(identificador)


def actualizar_productos(cursor, productos):
    cantidad = 0

    for producto in productos:
        identificador = producto["id_producto"]
        codigo = producto["codigo_barra"]
        nombre = producto["nombre_medicamento"]
        precio = Decimal(str(producto["precio_unitario"]))

        cursor.execute("""
            SELECT id_producto
            FROM productos
            WHERE codigo_barra = :codigo
        """, codigo=codigo)

        existente = cursor.fetchone()

        if existente:
            if existente[0] != identificador:
                raise ValueError(
                    "Conflicto de ID para producto " + codigo
                )

            cursor.execute("""
                UPDATE productos
                SET nombre_medicamento = :nombre,
                    precio_unitario = :precio,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE codigo_barra = :codigo
            """,
                nombre=nombre,
                precio=precio,
                codigo=codigo
            )

        else:
            cursor.execute("""
                SELECT codigo_barra
                FROM productos
                WHERE id_producto = :identificador
            """, identificador=identificador)

            if cursor.fetchone():
                raise ValueError(
                    "ID de producto ocupado por otro medicamento."
                )

            cursor.execute("""
                INSERT INTO productos (
                    id_producto,
                    codigo_barra,
                    nombre_medicamento,
                    precio_unitario,
                    stock_actual
                )
                VALUES (
                    :identificador, :codigo,
                    :nombre, :precio, 0
                )
            """,
                identificador=identificador,
                codigo=codigo,
                nombre=nombre,
                precio=precio
            )

        cantidad += 1

    return cantidad


def actualizar_clientes(cursor, clientes):
    cantidad = 0

    for cliente in clientes:
        cursor.execute("""
            SELECT id_cliente
            FROM clientes
            WHERE cedula = :cedula
        """, cedula=cliente["cedula"])

        existente = cursor.fetchone()

        if existente:
            # Conservar el cliente local y su ID.
            continue

        cursor.execute("""
            SELECT cedula
            FROM clientes
            WHERE id_cliente = :identificador
        """, identificador=cliente["id_cliente"])

        if cursor.fetchone():
            raise ValueError(
                "ID de cliente ocupado por otra cedula."
            )

        cursor.execute("""
            INSERT INTO clientes (
                id_cliente,
                cedula,
                nombre,
                telefono,
                nodo_origen,
                sincronizado
            )
            VALUES (
                :identificador,
                :cedula,
                :nombre,
                :telefono,
                :origen,
                1
            )
        """,
            identificador=cliente["id_cliente"],
            cedula=cliente["cedula"],
            nombre=cliente["nombre"],
            telefono=cliente["telefono"],
            origen=cliente["nodo_origen"]
        )

        cantidad += 1

    return cantidad


def importar_paquete():
    if not ruta.exists():
        print("No existe el paquete de CENTRAL.")
        return

    with open(ruta, "r", encoding="utf-8") as archivo:
        paquete = json.load(archivo)

    contenido, hash_paquete = verificar_paquete(paquete)
    validar_registros(contenido)

    with conectar_oracle() as conexion:
        cursor = conexion.cursor()

        try:
            cursor.execute("SELECT id_nodo FROM config_nodo")

            if cursor.fetchall() != [("SUC3",)]:
                raise ValueError("La base Oracle no es SUC3.")

            # Bloquear el control mientras se aplica el paquete.
            cursor.execute("""
                SELECT ultima_secuencia
                FROM control_catalogo_sync
                WHERE origen = 'CENTRAL'
                FOR UPDATE
            """)

            fila = cursor.fetchone()

            if fila is None:
                raise ValueError("No existe control de CENTRAL.")

            ultima = fila[0]
            secuencia = contenido["secuencia"]

            cursor.execute("""
                SELECT hash_sha256
                FROM paquetes_catalogo_recibidos
                WHERE id_paquete = :identificador
            """, identificador=contenido["id_paquete"])

            anterior = cursor.fetchone()

            if anterior:
                if not hmac.compare_digest(
                    anterior[0], hash_paquete
                ):
                    raise ValueError(
                        "Paquete repetido con contenido diferente."
                    )

                conexion.rollback()
                print("REPETIDO: paquete ya aplicado.")
                return

            if secuencia != ultima + 1:
                raise ValueError(
                    "Paquete fuera de orden. Se esperaba " +
                    str(ultima + 1)
                )

            total_productos = actualizar_productos(
                cursor, contenido["productos"]
            )

            total_clientes = actualizar_clientes(
                cursor, contenido["clientes"]
            )

            cursor.execute("""
                INSERT INTO paquetes_catalogo_recibidos (
                    id_paquete, origen, secuencia, hash_sha256
                )
                VALUES (
                    :identificador, 'CENTRAL',
                    :secuencia, :hash_paquete
                )
            """,
                identificador=contenido["id_paquete"],
                secuencia=secuencia,
                hash_paquete=hash_paquete
            )

            cursor.execute("""
                UPDATE control_catalogo_sync
                SET ultima_secuencia = :secuencia
                WHERE origen = 'CENTRAL'
            """, secuencia=secuencia)

            conexion.commit()

            print("Paquete aplicado correctamente.")
            print("Productos procesados:", total_productos)
            print("Clientes nuevos:", total_clientes)
            print("Secuencia aplicada:", secuencia)

        except Exception:
            conexion.rollback()
            raise


try:
    importar_paquete()

except Exception as error:
    print("Error al importar:", error)
