import getpass
import oracledb

# Usar los puertos publicados por Docker: CENTRAL 1525 y SUC3 1526.
# No se usa database link desde SUC3: Python abre cada conexion SOLO para probar el entorno.
for nombre, puerto in [('CENTRAL', 1525), ('SUC3', 1526)]:
    print('\n---', nombre, '---')
    usuario = input('Usuario de Oracle [FARMACIA]: ').strip() or 'FARMACIA'
    clave = getpass.getpass('Contrasena del usuario: ')
    dsn = f'127.0.0.1:{puerto}/XEPDB1'
    try:
        with oracledb.connect(user=usuario, password=clave, dsn=dsn) as conexion:
            with conexion.cursor() as cursor:
                cursor.execute('''SELECT USER, SYS_CONTEXT('USERENV','CON_NAME') FROM dual''')
                print('Conexion exitosa:', cursor.fetchone())
                cursor.execute('SELECT table_name FROM user_tables ORDER BY table_name')
                tablas = [fila[0] for fila in cursor]
                print('Tablas:', ', '.join(tablas) if tablas else '(ninguna)')
    except oracledb.Error as error:
        print('Fallo:', error)
