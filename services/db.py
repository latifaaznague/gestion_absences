import os
import psycopg2


DB_NAME = "gestion_absences"
DB_USER = "postgres"
DB_PASS = "123456"
DB_HOST = "localhost"
DB_PORT = "5432"


def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        client_encoding='UTF8'  # Ajoutez cette ligne
    )
    
    
    
    conn.set_client_encoding('UTF8')
    return conn