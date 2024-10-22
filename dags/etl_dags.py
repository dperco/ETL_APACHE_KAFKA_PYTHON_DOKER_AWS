from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
import json
import mysql.connector
import boto3

def produce_messages():
    conn = mysql.connector.connect(user='airflow', password='airflow', host='mysql', database='banco_clientes')
    cur = conn.cursor()
    cur.execute("SELECT * FROM clientes;")
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
    conn = mysql.connector.connect(user='airflow', password='airflow', host='mysql', database='banco_clientes')
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
                    (message.value['id'], message.value['nombre'], message.value['apellido'], message.value['direccion'], message.value['telefono'], message.value['caja_ahorro_pesos'], message.value['caja_ahorro_dolares']))
        conn.commit()
    cur.close()
    conn.close()

def upload_to_s3():
    conn = mysql.connector.connect(user='airflow', password='airflow', host='mysql', database='banco_clientes')
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