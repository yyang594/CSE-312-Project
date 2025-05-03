from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length, EqualTo, Regexp

# from PIL import Image
import requests
import database
import logging
import os
from html import escape
import secrets
import hashlib
import bcrypt

# --- Setup Logging ---

"""
LOG_DIR = '/logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
"""

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*")
db = database.get_db()
collection = db['items']
users_collection = db['users']
questions_collection = db['questions']
player_collection = db['players']
leaderboard_collection = db['leaderboard']

# ****Protects against CSRF attacks (CHANGE LATER)****
app.config['SECRET_KEY'] = 'temporary-very-weak-key'


class RegisterForm(FlaskForm):
    username = StringField('Username', [
        InputRequired(),
        Length(min=4)
    ])
    password = PasswordField('Password', [
        InputRequired(),
        Length(min=6, message='Password must be at least 6 characters long'),
        Regexp(r'^(?=.*\d)(?=.*[A-Z])(?=.*[a-z]).{6,}$',
               message="Password must contain at least one uppercase letter, one number, and be at least 6 characters long.")
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


# Routing
@app.route('/')
@app.route('/home')
def home():
    # Note to self: grab username from db and replace variable with it to display name
    auth_token = request.cookies.get('auth_token')
    username = "Guest"

    if auth_token:
        token_hash = hashlib.sha256(auth_token.encode()).hexdigest()
        user = users_collection.find_one({"auth_token": token_hash})

        if user:
            username = user['username']

    return render_template('home.html', username=username)

@app.route('/leaderboard', methods=['GET','POST'])
def leaderboard():
    #top_players = list(leaderboard_collection.find({}, {"_id": 0}).sort("score", -1).limit(10))
    return render_template('leaderboard.html')

@app.route('/game')
def game():
    room = request.args.get('room', 'default')
    return render_template('login.html', room=room)


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
        response.set_cookie("username", username, httponly=True, secure=True, samesite='Strict', max_age=3600)
        response.set_cookie("auth_token", token, httponly=True, secure=True, samesite='Strict', max_age=3600)
        return response
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    username = request.cookies.get('username')
    auth_token = request.cookies.get('auth_token')

    if username and auth_token:
        token_hash = hashlib.sha256(auth_token.encode()).hexdigest()

        user = users_collection.find_one({"username": username, "auth_token": token_hash})

        if user:
            users_collection.update_one({"username": username}, {"$set": {"auth_token": ""}})

    response = make_response(redirect(url_for('home')))

    response.set_cookie('username', '', expires=0)
    response.set_cookie('auth_token', '', expires=0)

    return response

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


player_data = {}


@socketio.on('move')
def handle_move(data):
    sid = request.sid
    user = player_data.get(sid, {})
    data.update({
        'name': user.get('username', 'Guest'),
        'image': user.get('profile_image', '/static/uploads/default.jpg'),
        'id': sid
    })
    room = user.get('room')
    if room:
        emit('player_moved', data, room=room)


@socketio.on('connect')
def handle_connect():
    auth_token = request.cookies.get('auth_token')
    username = "Guest"

    if auth_token:
        token_hash = hashlib.sha256(auth_token.encode()).hexdigest()
        user = users_collection.find_one({"auth_token": token_hash})
        if user:
            username = user['username']

    player_data[request.sid] = {"username": username}
    print(f"{username} connected with ID {request.sid}")


# --- Set up avatar uploads

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Lobby
rooms = {}
room_questions = {}
player_ready = {}


# https://opentdb.com/api.php?amount=${amount}&category=18&difficulty=medium&type=multiple
def fetch_trivia_questions(amount=50):
    response = requests.get(f"https://opentdb.com/api.php?amount={amount}&category=18&difficulty=medium&type=multiple")
    data = response.json()
    questions = []

    for result in data['results']:
        question = result['question']
        correct = result['correct_answer']
        incorrect = result['incorrect_answers']
        all_answers = incorrect + [correct]

        # Randomize answers
        import random
        random.shuffle(all_answers)

        questions.append({
            'question': question,
            'answers': all_answers,
            'solution': correct
        })
    return questions


@app.route('/lobby')
def lobby():
    return render_template('lobby.html')


@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    join_room(room)
    if room not in room_questions:
        room_questions[room] = []  # Placeholder, we'll fetch questions later
        player_ready[room] = {}
    player_ready[room][request.sid] = False  # Mark player as not ready


@socketio.on('player_ready')
def handle_player_ready(data):
    room = data['room']
    player_ready[room][request.sid] = True
    total_players = len(player_ready[room])
    ready_players = sum(1 for ready in player_ready[room].values() if ready)
    if ready_players / total_players >= 0.5:  # Majority ready
        if not room_questions[room]:  # Fetch if not already fetched
            room_questions[room] = fetch_trivia_questions()
        socketio.emit('start_game', {'questions': room_questions[room]}, room=room)


@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    room = player_data.get(sid, {}).get('room')
    if room and sid in rooms.get(room, []):
        rooms[room].remove(sid)
        if not rooms[room]:
            del rooms[room]
    player_data.pop(sid, None)


if __name__ == '__main__':
    # DELETE DEBUG LATER
    socketio.run(app, host='0.0.0.0', port=8080, allow_unsafe_werkzeug=True, debug=False)