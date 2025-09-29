from flask import Flask, request, jsonify, render_template, session, redirect
import pymysql
import os, sys
import json
import requests
from bs4 import BeautifulSoup
import feedparser
import urllib.request
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import time
from datetime import timedelta

from dotenv import load_dotenv
load_dotenv()
import configparser
cfg = configparser.ConfigParser()
cfg.read(os.path.join(os.getcwd(), '.env'))

import pprint
pp = pprint.PrettyPrinter(indent=4)

import jetTools
import jetDB

jetTools.initDB()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)


app.secret_key = "G3nPy4pp!"
app.permanent_session_lifetime = timedelta(days=7)

app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.route('/')
def home():
    return render_template("index.html")


@app.route('/testLocalPostGresSQL')
def dbTest():
    return "testLocalPostGresSQL"
    
    PG_DSN = "postgresql+psycopg://appuser:appsecret@localhost:5432/appdb"
    # create a table
    print(jetDB.dbExecute(PG_DSN, """
    CREATE TABLE IF NOT EXISTS testTable (
      id BIGSERIAL PRIMARY KEY,
      rantext TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """, return_rows=False))

    # insert a row
    print(jetDB.dbExecute(PG_DSN,
        "INSERT INTO users (rantext) VALUES (:rantext) RETURNING id, email",
        params={"rantext":"12345"},
        return_rows=True))

    # select
    print(jetDB.dbExecute(PG_DSN,
        "SELECT id, rantext FROM users testTable BY id DESC"))




@app.route('/register', methods=['GET', 'POST'])
def register():
    user_email = session.get('user_email')
    if (not user_email) or (user_email != cfg["settings"]["admin_email"]):
        return "You must be the Admin to register a user."
        #return redirect('/login')
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hash_pw = generate_password_hash(password)
        # Check if email already exists
        check = jetTools.dbQuery("SELECT * FROM users WHERE email = ?", (email,))
        if not check["success"]:
            return f"Database error: {check['error']}", 500
        if check["data"]:
            return "Email already registered.", 400
        # Insert user
        insert = jetTools.dbQuery(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, hash_pw)
        )
        if not insert["success"]:
            return f"Insert error: {insert['error']}", 500
        session['user_email'] = email
        return redirect('/')
    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        result = jetTools.dbQuery("SELECT * FROM users WHERE email = ?", (email,))
        if not result["success"]:
            return f"Database error: {result['error']}", 500
        if not result["data"]:
            return "No user found with that email.", 400
        user = result["data"][0]
        if check_password_hash(user["password_hash"], password):
            session.permanent = True
            session['user_email'] = user["email"]
            return redirect('/')
        else:
            return "Incorrect password.", 400
    return render_template('login.html')



@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect('/')


@app.route('/users')
def view_users():
    result = jetTools.dbQuery("SELECT id, email FROM users ORDER BY id ASC")
    users = result.get("data") or []  # Ensures it's always a list
    return render_template("view-users.html", users=users)







@app.route("/admin/users")
def admin_users():
    if session.get("user_email") not in jetTools.ADMINS:
        return "Unauthorized", 403
    result = jetTools.dbQuery("SELECT email FROM users")
    if not result["success"]:
        return "Database error", 500
    return render_template("manage-users.html", users=result["data"])

@app.route("/admin/add-user", methods=["POST"])
def admin_add_user():
    if session.get("user_email") not in jetTools.ADMINS:
        return jsonify({"message": "Unauthorized"}), 403
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"message": "Missing fields"}), 400
    password_hash = generate_password_hash(password)
    result = jetTools.dbQuery(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        params=(email, password_hash)
    )
    if result["success"]:
        return jsonify({"message": "User added successfully."})
    else:
        return jsonify({"message": f"Error: {result['error']}"}), 500

@app.route("/admin/edit-user", methods=["POST"])
def admin_edit_user():
    if session.get("user_email") not in jetTools.ADMINS:
        return jsonify({"message": "Unauthorized"}), 403
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"message": "Missing fields"}), 400
    password_hash = generate_password_hash(password)
    result = jetTools.dbQuery(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        params=(password_hash, email)
    )
    if result["success"]:
        return jsonify({"message": "Password updated."})
    else:
        return jsonify({"message": f"Error: {result['error']}"}), 500

@app.route("/admin/delete-user", methods=["POST"])
def admin_delete_user():
    if session.get("user_email") not in jetTools.ADMINS:
        return jsonify({"message": "Unauthorized"}), 403
    data = request.get_json()
    email = data.get("email")
    result = jetTools.dbQuery(
        "DELETE FROM users WHERE email = ?",
        params=(email,)
    )
    if result["success"]:
        return jsonify({"message": "User deleted."})
    else:
        return jsonify({"message": f"Error: {result['error']}"}), 500










if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)





