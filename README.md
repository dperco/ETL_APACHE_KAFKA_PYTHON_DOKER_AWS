Este README proporciona una guía paso a paso para configurar Apache Airflow en Windows utilizando Docker, incluyendo la generación de una clave Fernet, la configuración de la base de datos MySQL, la creación de un pipeline de datos con datos aleatorios generados con Faker, la integración con Apache Kafka para un pipeline ETL, y el almacenamiento de los resultados en AWS S3.

Prerrequisitos
Docker Desktop instalado en Windows.
Python instalado en tu sistema.
Conexión a Internet para descargar las imágenes de Docker y las bibliotecas necesarias.
Una cuenta de AWS con permisos para acceder a S3.
AWS CLI instalado y configurado.
Paso 1: Instalar Docker Desktop
Descarga e instala Docker Desktop desde la página oficial de Docker.
Asegúrate de que Docker Desktop esté en ejecución.
Paso 2: Generar una clave Fernet
La clave Fernet se utiliza para encriptar y desencriptar datos sensibles en Apache Airflow.

Instalar la biblioteca cryptography:

sh
pip install cryptography
Crear un script para generar la clave Fernet:

Crea un archivo llamado generate_fernet_key.py con el siguiente contenido:

python
from cryptography.fernet import Fernet

# Generar una clave Fernet
fernet_key = Fernet.generate_key()
print(fernet_key.decode())  # Imprimir la clave en formato legible
Ejecutar el script:

sh
python generate_fernet_key.py
Esto imprimirá una clave Fernet en la terminal. Guarda esta clave, ya que la necesitarás para configurar Airflow.

Paso 3: Configurar Docker Compose para Airflow, Kafka y MySQL
Crear un archivo docker-compose.yml en el directorio de tu proyecto con el siguiente contenido:

yaml
version: '3'
services:
  mysql:
    image: mysql:5.7
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: bank
      MYSQL_USER: airflow
      MYSQL_PASSWORD: airflow
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  zookeeper:
    image: wurstmeister/zookeeper:3.4.6
    ports:
      - "2181:2181"

  kafka:
    image: wurstmeister/kafka:2.12-2.2.1
    ports:
      - "9092:9092"
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  webserver:
    image: apache/airflow:2.1.2
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__SQL_ALCHEMY_CONN: mysql+mysqlconnector://airflow:airflow@mysql/bank
      AIRFLOW__CORE__FERNET_KEY: 'YOUR_FERNET_KEY'
      AIRFLOW__CORE__LOAD_EXAMPLES: 'true'
      AWS_ACCESS_KEY_ID: 'YOUR_AWS_ACCESS_KEY_ID'
      AWS_SECRET_ACCESS_KEY: 'YOUR_AWS_SECRET_ACCESS_KEY'
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
    ports:
      - "8080:8080"
    depends_on:
      - mysql
      - kafka
    command: webserver

  scheduler:
    image: apache/airflow:2.1.2
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__SQL_ALCHEMY_CONN: mysql+mysqlconnector://airflow:airflow@mysql/bank
      AIRFLOW__CORE__FERNET_KEY: 'YOUR_FERNET_KEY'
      AIRFLOW__CORE__LOAD_EXAMPLES: 'true'
      AWS_ACCESS_KEY_ID: 'YOUR_AWS_ACCESS_KEY_ID'
      AWS_SECRET_ACCESS_KEY: 'YOUR_AWS_SECRET_ACCESS_KEY'
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
    depends_on:
      - mysql
      - kafka
    command: scheduler

volumes:
  mysql_data:
Reemplaza 'YOUR_FERNET_KEY', 'YOUR_AWS_ACCESS_KEY_ID' y 'YOUR_AWS_SECRET_ACCESS_KEY' con tus credenciales de AWS y la clave Fernet generada en el paso anterior.

Paso 4: Iniciar los servicios de Airflow, Kafka y MySQL
Iniciar los servicios de Airflow, Kafka y MySQL utilizando Docker Compose:

sh
docker-compose up -d
Acceder a la interfaz web de Airflow:

Abre tu navegador y ve a http://localhost:8080 para acceder a la interfaz web de Airflow.

Paso 5: Crear un pipeline ETL en Airflow con datos aleatorios y almacenamiento en AWS S3
Instalar las bibliotecas necesarias:

sh
pip install faker boto3 kafka-python mysql-connector-python
Crear un script para generar y cargar datos aleatorios en MySQL:

Crea un archivo llamado generate_and_load_data.py con el siguiente contenido:

python
from faker import Faker
import mysql.connector

fake = Faker()

def generate_and_load_data():
    conn = mysql.connector.connect(user='airflow', password='airflow', host='localhost', database='bank')
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(255),
            apellido VARCHAR(255),
            direccion TEXT,
            telefono VARCHAR(20),
            caja_ahorro_pesos DECIMAL(10, 2),
            caja_ahorro_dolares DECIMAL(10, 2)
        );
    """)
    for _ in range(100):
        nombre = fake.first_name()
        apellido = fake.last_name()
        direccion = fake.address()
        telefono = fake.phone_number()
        caja_ahorro_pesos = fake.pydecimal(left_digits=5, right_digits=2, positive=True)
        caja_ahorro_dolares = fake.pydecimal(left_digits=5, right_digits=2, positive=True)
        cur.execute("INSERT INTO customers (nombre, apellido, direccion, telefono, caja_ahorro_pesos, caja_ahorro_dolares) VALUES (%s, %s, %s, %s, %s, %s);",
                    (nombre, apellido, direccion, telefono, caja_ahorro_pesos, caja_ahorro_dolares))
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    generate_and_load_data()
Ejecutar el script para generar y cargar datos:

sh
python generate_and_load_data.py
Crear un archivo DAG:

Crea un archivo DAG en el directorio dags (por ejemplo, dags/etl_dag.py) con el siguiente contenido:

python
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
import json
import mysql.connector
import boto3

def produce_messages():
    conn = mysql.connector.connect(user='airflow', password='airflow', host='mysql', database='bank')
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers;")
    rows = cur.fetchall()
    producer = KafkaProducer(bootstrap_servers='kafka:9092', value_serializer=lambda v: json.dumps(v).encode('utf-8'))
    for row in rows:
        message = {
            'id': row[0],
            'nombre': row[1],
            'apellido': row[2],
            'direccion': row[3],
            'telefono': row[4],
            'caja_ahorro_pesos': float(row[5]),
            'caja_ahorro_dolares': float(row[6])
        }
        producer.send('bank_customers', message)
    producer.flush()
    cur.close()
    conn.close()

def consume_and_store_data():
    consumer = KafkaConsumer('bank_customers', bootstrap_servers='kafka:9092', value_deserializer=lambda m: json.loads(m.decode('utf-8')))
    conn = mysql.connector.connect(user='airflow', password='airflow', host='mysql', database='bank')
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS processed_customers (
            id INT PRIMARY KEY,
            nombre VARCHAR(255),
            apellido VARCHAR(255),
            direccion TEXT,
            telefono VARCHAR(20),
            caja_ahorro_pesos DECIMAL(10, 2),
            caja_ahorro_dolares DECIMAL(10, 2)
        );
    """)
    for message in consumer:
        cur.execute("INSERT INTO processed_customers (id, nombre, apellido, direccion, telefono, caja_ahorro_pesos, caja_ahorro_dolares) VALUES (%s, %s, %s, %s, %s, %s, %s);",
                    (message['id'], message['nombre'], message['apellido'], message['direccion'], message['telefono'], message['caja_ahorro_pesos'], message['caja_ahorro_dolares']))
        conn.commit()
    cur.close()
    conn.close()

def upload_to_s3():
    conn = mysql.connector.connect(user='airflow', password='airflow', host='mysql', database='bank')
    cur = conn.cursor()
    cur.execute("SELECT * FROM processed_customers;")
    rows = cur.fetchall()
    data = [dict(id=row[0], nombre=row[1], apellido=row[2], direccion=row[3], telefono=row[4], caja_ahorro_pesos=float(row[5]), caja_ahorro_dolares=float(row[6])) for row in rows]
    s3 = boto3.client('s3')
    s3.put_object(Bucket='YOUR_S3_BUCKET_NAME', Key='etl_output.json', Body=json.dumps(data))
    cur.close()
    conn.close()

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

dag = DAG(
    'etl_dag',
    default_args=default_args,
    description='A simple ETL DAG with Kafka and AWS S3',
    schedule_interval='@daily',
)

start = DummyOperator(
    task_id='start',
    dag=dag,
)

produce_task = PythonOperator(
    task_id='produce_messages',
    python_callable=produce_messages,
    dag=dag,
)

consume_task = PythonOperator(
    task_id='consume_and_store_data',
    python_callable=consume_and_store_data,
    dag=dag,
)

upload_task = PythonOperator(
    task_id='upload_to_s3',
    python_callable=upload_to_s3,
    dag=dag,
)

start >> produce_task >> consume_task >> upload_task
Reemplaza 'YOUR_S3_BUCKET_NAME' con el nombre de tu bucket de S3.

Verificar el DAG en la interfaz web de Airflow:

Ve a la interfaz web de Airflow y verifica que el DAG etl_dag aparece en la lista de DAGs.

Paso 6: Configurar la base de datos
La configuración de la base de datos ya está incluida en el archivo docker-compose.yml con el servicio mysql. Los detalles de conexión se especifican en las variables de entorno:

MYSQL_ROOT_PASSWORD: Contraseña del usuario root de MySQL (por defecto: root).
MYSQL_DATABASE: Nombre de la base de datos (por defecto: bank).
MYSQL_USER: Nombre de usuario de la base de datos (por defecto: airflow).
MYSQL_PASSWORD: Contraseña de la base de datos (por defecto: airflow).
Resumen
Instalar Docker Desktop.
Generar una clave Fernet utilizando la biblioteca cryptography.
Configurar Docker Compose para Airflow, Kafka y MySQL.
Iniciar los servicios de Airflow, Kafka y MySQL utilizando Docker Compose.
Crear un script para generar y cargar datos aleatorios en MySQL.
Crear un pipeline ETL en Airflow con datos aleatorios y almacenamiento en AWS S3.
Configurar la base de datos utilizando MySQL.
Siguiendo estos pasos, deberías poder configurar y ejecutar Apache Airflow en Windows utilizando Docker, generar una clave Fernet, configurar la base de datos, crear un pipeline de datos con datos aleatorios generados con Faker, integrar Apache Kafka para un pipeline ETL, y almacenar los resultados en AWS S3.




     


    




     


  
 



Crear un pipeline ETL en Airflow con datos aleatorios y almacenamiento en AWS S3.
Configurar la base de datos utilizando MySQL.
Siguiendo estos pasos, deberías poder configurar y ejecutar Apache Airflow en Windows utilizando Docker, generar una clave Fernet, configurar la base de datos, crear un pipeline de datos con datos aleatorios generados con Faker, integrar Apache Kafka para un pipeline ETL, y almacenar los resultados en AWS S3.

