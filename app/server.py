from flask import Flask, jsonify, request
import database
import logging
import os

# --- Setup Logging ---
LOG_DIR = '/logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
app = Flask(__name__)
db = database.get_db()
collection = db['items']
@app.route('/')
def home():
    return "Welcome to the EVIL KAHOOT!"

@app.route('/items')
def get_items():
    items = list(collection.find({}, {'_id': 0}))
    return jsonify(items)

@app.route('/add-item')
def add_item():
    collection.insert_one({"name": "Test Item"})
    return jsonify({"status": "item added"})

@app.before_request
def log_request():
    ip = request.remote_addr
    method = request.method
    path = request.path
    logging.info(f"{ip} {method} {path}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
