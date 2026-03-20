# database/mysql_handler.py
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("MYSQL_HOST", "localhost"),
    "user":     os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "affidavit_db"),
}

CREATE_DB_SQL = "CREATE DATABASE IF NOT EXISTS affidavit_db;"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS affidavit_extractions (
    id                  INT AUTO_INCREMENT PRIMARY KEY,

    -- Source
    source_file         VARCHAR(255),
    extracted_at        DATETIME,

    -- Personal Info
    full_name           VARCHAR(255),
    fathers_name        VARCHAR(255),
    age                 INT,
    address             TEXT,
    mobile              VARCHAR(20),

    -- Election Info
    constituency_number VARCHAR(10),
    constituency_name   VARCHAR(255),
    affidavit_number    VARCHAR(50),

    -- Financial / PAN
    pan_number          VARCHAR(10),
    pan_valid           TINYINT(1),     -- 1 = valid, 0 = invalid
    pan_confidence      VARCHAR(10),    -- 'high' | 'medium' | 'low'

    -- Metadata
    ocr_engine          VARCHAR(50),
    extraction_status   VARCHAR(20),    -- 'success' | 'partial' | 'failed'

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_source_file (source_file)
);
"""

#connection handling

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"[mysql_handler] Connection error: {e}")
        raise

def setup_database():
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"]
        )
        cursor = conn.cursor()
        cursor.execute(CREATE_DB_SQL)
        print("[mysql_handler] Database 'affidavit_db' ready.")

        cursor.execute(f"USE {DB_CONFIG['database']};")
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()
        print("[mysql_handler] Table 'affidavit_extractions' ready.")

        cursor.close()
        conn.close()

    except Error as e:
        print(f"[mysql_handler] Setup error: {e}")
        raise

#insert and query functions

INSERT_SQL = """
INSERT INTO affidavit_extractions (
    source_file, extracted_at,
    full_name, fathers_name, age, address, mobile,
    constituency_number, constituency_name, affidavit_number,
    pan_number, pan_valid, pan_confidence,
    ocr_engine, extraction_status
) VALUES (
    %(source_file)s, %(extracted_at)s,
    %(full_name)s, %(fathers_name)s, %(age)s, %(address)s, %(mobile)s,
    %(constituency_number)s, %(constituency_name)s, %(affidavit_number)s,
    %(pan_number)s, %(pan_valid)s, %(pan_confidence)s,
    %(ocr_engine)s, %(extraction_status)s
)
ON DUPLICATE KEY UPDATE
    extracted_at       = VALUES(extracted_at),
    extraction_status  = VALUES(extraction_status);
"""

def insert_extraction(data: dict) -> int:
    """
    Inserts one extracted affidavit record.
    Returns the new row's auto-incremented ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(INSERT_SQL, data)
        conn.commit()
        row_id = cursor.lastrowid
        if row_id:
            print(f"[mysql_handler] Inserted row ID: {row_id}")
        else:
            print(f"[mysql_handler] Duplicate skipped: {data.get('source_file')}")
        return row_id
    except Error as e:
        conn.rollback()
        print(f"[mysql_handler] Insert error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def find_by_pan(pan: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM affidavit_extractions WHERE pan_number = %s LIMIT 1;",
        (pan,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def get_all_extractions() -> list:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM affidavit_extractions ORDER BY created_at DESC;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows