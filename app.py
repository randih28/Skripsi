from flask import Flask, jsonify
from flask_mysqldb import MySQL
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Ganti dengan secret key yang kuat

# Config database
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'datasiswa'

mysql = MySQL(app)

# Setup logging
logging.basicConfig(filename='app.log', level=logging.DEBUG)

# Mengimpor rute dari file routes.py
from routes import *

if __name__ == '__main__':
    app.run(debug=True)
