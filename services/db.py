import psycopg2
from psycopg2.extras import RealDictCursor

DB_HOST = "localhost"
DB_NAME = "absenceflow"
DB_USER = "postgres"
DB_PASSWORD = "ton_motdepasse"
DB_PORT = 5432

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if fetch_one:
            result = cur.fetchone()
        elif fetch_all:
            result = cur.fetchall()
        else:
            result = None
        conn.commit()
        return result
    finally:
        cur.close()
        conn.close()
