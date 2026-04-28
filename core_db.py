import time
from decimal import Decimal

import mysql.connector

from core_config import (
    STOCKS_MYSQL_HOST,
    STOCKS_MYSQL_PORT,
    STOCKS_MYSQL_USER,
    STOCKS_MYSQL_PASSWORD,
    STOCKS_MYSQL_DATABASE,
    DB_MAX_RETRIES,
    DB_RETRY_DELAY,
)


def db_connection():
    return mysql.connector.connect(
        host=STOCKS_MYSQL_HOST,
        port=STOCKS_MYSQL_PORT,
        user=STOCKS_MYSQL_USER,
        password=STOCKS_MYSQL_PASSWORD,
        database=STOCKS_MYSQL_DATABASE,
        autocommit=False,
    )


def wait_for_db():
    last_error = None
    for attempt in range(1, DB_MAX_RETRIES + 1):
        try:
            conn = db_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            conn.close()
            print(f"[startup] stocks_db listo en intento {attempt}")
            return
        except Exception as exc:
            last_error = exc
            print(f"[startup] esperando stocks_db ({attempt}/{DB_MAX_RETRIES}): {exc}")
            time.sleep(DB_RETRY_DELAY)

    raise RuntimeError(f"No fue posible conectar a stocks_db: {last_error}")


def decimal_to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def rows_to_dicts(cursor, rows):
    cols = [col[0] for col in cursor.description]
    output = []
    for row in rows:
        item = {}
        for idx, value in enumerate(row):
            item[cols[idx]] = decimal_to_float(value)
        output.append(item)
    return output