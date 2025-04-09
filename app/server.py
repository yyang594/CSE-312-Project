from flask import Flask, jsonify, make_response, redirect, render_template, request, url_for
import database
import logging
import os

# --- Setup Logging ---
"""LOG_DIR = '/logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)"""
app = Flask(__name__)
db = database.get_db()
collection = db['items']

#Routing
@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/login', methods = ['GET','POST'])
def login():
    return render_template('login.html')

@app.route('/register', methods = ['GET','POST'])
def register():
    if request.method == 'POST':
        #Request info accessed here. Authenticate
        """
        Testing
        print(f"METHOD: {request.method}")
        print(f"REQUEST FORM: {request.form}")
        print(f"USERNAME: {request.form['username']}")
        """
        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/test')
def test():
    resp = make_response(render_template('home.html'))
    resp.set_cookie('somecookiename', 'I am cookie')
    return resp 

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
