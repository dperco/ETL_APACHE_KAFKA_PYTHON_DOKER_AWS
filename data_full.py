import mysql.connector
from faker import Faker
import random

# Conectar a la base de datos MySQL
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='Zaq12wsx.',
    database='banco_clientes'
)

cursor = conn.cursor()

# Crear una instancia de Faker
fake = Faker()

# Generar y insertar datos aleatorios
for _ in range(100000):  # Generar 100000 registros
    nombre = fake.first_name()
    apellido = fake.last_name()
    direccion = fake.address()
    telefono = fake.phone_number()
    caja_ahorro_pesos = round(random.uniform(0, 100000), 2)
    caja_ahorro_dolares = round(random.uniform(0, 10000), 2)

    # Insertar los datos en la tabla
    cursor.execute("""
        INSERT INTO clientes (nombre, apellido, direccion, telefono, caja_ahorro_pesos, caja_ahorro_dolares)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nombre, apellido, direccion, telefono, caja_ahorro_pesos, caja_ahorro_dolares))

# Confirmar los cambios
conn.commit()

# Cerrar la conexión
cursor.close()
conn.close()