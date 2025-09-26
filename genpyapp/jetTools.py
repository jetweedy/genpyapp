
import pymysql
import os, sys
import json
import sqlite3
from bs4 import BeautifulSoup
import pandas as pd
import requests
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()
import configparser
cfg = configparser.ConfigParser()
cfg.read(os.path.join(os.getcwd(), '.env'))

from werkzeug.security import generate_password_hash, check_password_hash

import pprint
pp = pprint.PrettyPrinter(indent=4)


ADMINS = [cfg["settings"]["admin_email"]]


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(BASE_DIR, "/data/app.db"))



def get_db_connection(autocommit=True):
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        cursorclass=pymysql.cursors.DictCursor,  # Return results as dicts
        autocommit=autocommit,
    )



def dbQuery(query, params=()):
    result = {"success": False, "data": None, "error": None}
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row  # allows dict-like row access
        cur = conn.cursor()
        cur.execute(query, params)
        query_type = query.strip().split()[0].upper()
        if query_type == "SELECT":
            rows = cur.fetchall()
            result["data"] = [dict(row) for row in rows]
        else:
            conn.commit()
            result["data"] = {
                "rowcount": cur.rowcount,
                "lastrowid": cur.lastrowid if query_type == "INSERT" else None
            }
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    finally:
        conn.close()
    return result


def initDB():
    # Resolve default to the folder containing this file
    base_dir = Path(__file__).resolve().parent
    default_db = base_dir / "data/app.db"

    # Allow env override, but normalize to an absolute path
    env_path = os.getenv("SQLITE_DB_PATH")
    db_path = Path(env_path).expanduser().resolve() if env_path else default_db

    print("=== SQLite init ===")
    print(" __file__:", __file__)
    print(" base_dir:", base_dir)
    print(" SQLITE_DB_PATH (effective):", repr(str(db_path)))

    # Ensure destination directory exists
    db_dir = db_path.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    print(" db_dir exists:", db_dir.exists(), " | writable:", os.access(db_dir, os.W_OK))

    # Create / migrate schema
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
        """)
        conn.commit()
        result = dbQuery(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            params=(cfg["settings"]["admin_email"], generate_password_hash(cfg["settings"]["admin_password"]))
        )
    finally:
        conn.close()

    # Verify the file is actually there
    exists = db_path.exists()
    size = db_path.stat().st_size if exists else 0
    print(" created:", exists, " | size bytes:", size)


