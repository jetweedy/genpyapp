
import pymysql
import os, sys
import json
import sqlite3
from bs4 import BeautifulSoup
import pandas as pd
import requests

from dotenv import load_dotenv
load_dotenv()

import configparser
cfg = configparser.ConfigParser()
cfg.read(os.getcwd()+'/config.ini')
import pprint
pp = pprint.PrettyPrinter(indent=4)


ADMINS = ["jetweedy@gmail.com"]
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/data/app.db")



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
    db_dir = os.path.dirname(SQLITE_DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    # Example table creation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            symbol TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_email, symbol)
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()




