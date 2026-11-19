
import oracledb
from getpass import getpass


def conectar_oracle():
    contrasena = getpass("Contraseña de FARMACIA_SUC3: ")

    conexion = oracledb.connect(
        user="FARMACIA_SUC3",
        password=contrasena,
        host="localhost",
        port=1521,
        service_name="XEPDB1"
    )

    return conexion


if __name__ == "__main__":
    try:
        with conectar_oracle() as conexion:
            cursor = conexion.cursor()

            cursor.execute("""
                SELECT USER,
                       SYS_CONTEXT('USERENV', 'CON_NAME')
                FROM dual
            """)

            resultado = cursor.fetchone()

            print("Conexion exitosa con Oracle")
            print("Usuario:", resultado[0])
            print("Contenedor:", resultado[1])

    except oracledb.Error as error:
        print("Error de Oracle:", error)
