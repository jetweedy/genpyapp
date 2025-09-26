
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


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#print("BASE_DIR:", BASE_DIR)
SQLITE_DB_PATH = os.path.join(BASE_DIR, "data/app.db")
#print("SQLITE_DB_PATH:", SQLITE_DB_PATH)




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

    db_path = SQLITE_DB_PATH
    print("db_path:", db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

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



