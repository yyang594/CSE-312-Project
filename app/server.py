from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length, EqualTo, Regexp

import database
import logging
import os
from html import escape
import secrets
import hashlib
import bcrypt

# --- Setup Logging ---

"""LOG_DIR = '/logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)"""

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*")
db = database.get_db()
collection = db['items']
users_collection = db['users']

#****Protects against CSRF attacks (CHANGE LATER)****
app.config['SECRET_KEY'] = 'temporary-very-weak-key'

class RegisterForm(FlaskForm):
    username = StringField('Username', [
        InputRequired(), 
        Length(min=4)
    ])
    password = PasswordField('Password', [
        InputRequired(), 
        Length(min=6, message='Password must be at least 6 characters long'),
        Regexp(r'^(?=.*\d)(?=.*[A-Z])(?=.*[a-z]).{6,}$', message="Password must contain at least one uppercase letter, one number, and be at least 6 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', [
        InputRequired(),
        EqualTo('password', message='Passwords must match')
    ])

class LoginForm(FlaskForm):
    username = StringField('Username', [
        InputRequired(), 
        Length(min=4)
    ])
    password = PasswordField('Password', [
        InputRequired(), 
        Length(min=6, message='Incorrect Password')
    ])

#Routing
@app.route('/')
@app.route('/home')
def home():
    #Note to self: grab username from db and replace variable with it to display name
    auth_token = request.cookies.get('auth_token')
    username = "Guest"

    if auth_token:
        token_hash = hashlib.sha256(auth_token.encode()).hexdigest()
        user = users_collection.find_one({"auth_token": token_hash})

        if user:
            username = user['username']

    return render_template('home.html', username=username)

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        username = escape(form.username.data)
        password = form.password.data

        user = users_collection.find_one({"username": username})

        if not user or not bcrypt.checkpw(password.encode(), user["password"]):
            return jsonify({"success": False, "message": "Invalid credentials."}), 401

        token = secrets.token_hex(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        users_collection.update_one({"username": username}, {"$set": {"auth_token": token_hash}})

        response = make_response(redirect(url_for('home')))
        response.set_cookie("username", username, httponly=True, secure=True, samesite='Strict')
        response.set_cookie("auth_token", token, httponly=True, secure=True, samesite='Strict', max_age=3600)
        return response
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        username = escape(form.username.data)
        password = form.password.data
        confirm_password = form.confirm_password.data

        if users_collection.find_one({"username": username}):
            return jsonify({"success": False, "message": "Username already taken."}), 400

        if password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match."}), 400

        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        users_collection.insert_one({
            "username": username,
            "password": hashed_pw
        })
        
        return redirect(url_for('home'))
    
    return render_template('register.html', form=form)

@app.route('/submit_question', methods=['GET', 'POST'])
def submit_question():
    if request.method == 'POST':
        questions = request.form.getlist('question[]')
        possibleAnswers = request.form.getlist('answer[]')
        correct_answers = request.form.getlist('correct_answer[]')
        #Unfortunately the data's pretty ugly but questions/correct_answers is a list of questions/correct_answers
        #posibleAnswers is a list of all possible answers, each 4 answers correspond to a question in order
        #Note: edge cases: check for no correct answers
        #                  check how many answers are actually submitted
    
    return render_template('question_submission.html')

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

@socketio.on('move')
def handle_move(data):
    emit('player_moved', data, broadcast=True, include_self=False)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, allow_unsafe_werkzeug=True)
