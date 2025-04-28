from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length, EqualTo, Regexp

import requests
import random
import database
import logging
import os
from html import escape
import secrets
import hashlib
import bcrypt

# --- Setup Logging ---

LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*")
db = database.get_db()
collection = db['items']
users_collection = db['users']
questions_collection = db['questions']
player_collection = db['players']

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
    auth_token = request.cookies.get('auth_token')
    username = "Guest"

    if auth_token:
        token_hash = hashlib.sha256(auth_token.encode()).hexdigest()
        user = users_collection.find_one({"auth_token": token_hash})

        if user:
            username = user['username']

    return render_template('home.html', username=username)

@app.route('/lobby')
def lobby():
    return render_template('lobby.html')

@app.route('/game')
def game():
    room = request.args.get('room', 'default')
    return render_template('game.html', room=room)

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

@socketio.on('request_next_question')
def handle_request_next_question(data):
    room = data['room']
    questions = lobbies.get(room, {}).get('questions', [])

    if questions:
        next_question = questions.pop(0)

        # Before sending the question, save the correct answer's box
        correct_index = next_question['answers'].index(next_question['solution'])

        # Find the correct box (same order as frontend)
        canvas_width = 1920 - 275  # Match your frontend Canvas width
        canvas_height = 1080

        rect_width = canvas_width * 0.4
        rect_height = canvas_height * 0.4

        if correct_index == 0:
            correct_zone = (0, 0, rect_width, rect_height)
        elif correct_index == 1:
            correct_zone = (canvas_width - rect_width, 0, rect_width, rect_height)
        elif correct_index == 2:
            correct_zone = (0, canvas_height - rect_height, rect_width, rect_height)
        elif correct_index == 3:
            correct_zone = (canvas_width - rect_width, canvas_height - rect_height, rect_width, rect_height)
        else:
            correct_zone = None  # Shouldn't happen

        # 🚀 Save correct zone on server
        lobbies[room]['correct_zone'] = correct_zone

        socketio.emit('next_question', next_question, room=room)

    else:
        print(f"No more questions left in room {room}. Game Over!")

        players = lobbies.get(room, {}).get('players', {})
        if players:
            winner_sid = max(players, key=lambda sid: players[sid].get('score', 0))
            winner = players[winner_sid]

            socketio.emit('game_over', {
                'winnerName': winner['username'],
                'winnerScore': winner.get('score', 0)
            }, room=room)

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

    # ✅ Update the player's own server position
    user['x'] = data['x']
    user['y'] = data['y']

    # Update player_data dictionary
    player_data[sid] = user

    data.update({
        'name': user.get('username', 'Guest'),
        'image': user.get('profile_image', '/static/uploads/default.jpg'),
        'id': sid
    })
    room = user.get('room')
    if room:
        emit('player_moved', data, room=room)

@socketio.on('player_push')
def handle_player_push(data):
    room = data['room']
    sid = request.sid

    push_x = data['x']
    push_y = data['y']

    push_radius = 150  # How far the push can reach
    push_strength = 50  # How much to move the players away

    if not room or room not in lobbies:
        return

    # Move players away if they are close enough
    for other_sid, pdata in lobbies[room]['players'].items():
        if other_sid == sid:
            continue  # Don't push yourself

        other_pos = player_data.get(other_sid, {})
        ox = other_pos.get('x')
        oy = other_pos.get('y')

        if ox is None or oy is None:
            continue

        dx = ox - push_x
        dy = oy - push_y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance < push_radius and distance != 0:
            # Calculate push
            factor = (push_radius - distance) / push_radius
            move_x = (dx / distance) * push_strength * factor
            move_y = (dy / distance) * push_strength * factor

            # Update server position
            player_data[other_sid]['x'] = ox + move_x
            player_data[other_sid]['y'] = oy + move_y

    # Broadcast updated player positions after the push
    broadcast_players = {}
    for sid, pdata in player_data.items():
        if pdata.get('room') == room:
            broadcast_players[sid] = {
                'x': pdata.get('x', 0),
                'y': pdata.get('y', 0),
                'name': pdata.get('username', 'Guest')
            }

    socketio.emit('update_positions', broadcast_players, room=room)

@socketio.on('sync_positions')
def handle_sync_positions(data):
    room = data['room']
    updated_players = data['players']

    # Update player_data with the new positions
    for sid, player_info in updated_players.items():
        if sid in player_data:
            player_data[sid]['x'] = player_info['x']
            player_data[sid]['y'] = player_info['y']

    # Create a clean payload to send back
    broadcast_players = {}
    for sid, pdata in player_data.items():
        broadcast_players[sid] = {
            'x': pdata.get('x', 0),
            'y': pdata.get('y', 0),
            'name': pdata.get('username', 'Guest')
        }

    socketio.emit('update_positions', broadcast_players, room=room)

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

@socketio.on('submit_answer')
def handle_submit_answer(data):
    sid = request.sid
    room = player_data.get(sid, {}).get('room')
    x = data['x']
    y = data['y']

    if not room or room not in lobbies:
        return

    correct_zone = lobbies[room].get('correct_zone')
    if not correct_zone:
        return

    zone_x, zone_y, zone_w, zone_h = correct_zone

    # Update player score if they are correct
    if zone_x <= x <= zone_x + zone_w and zone_y <= y <= zone_y + zone_h:
        lobbies[room]['players'][sid]['score'] = lobbies[room]['players'][sid].get('score', 0) + 200

    # Mark that this player answered
    lobbies[room]['players'][sid]['answered'] = True

    # Check if ALL players have answered
    all_answered = all(player.get('answered') for player in lobbies[room]['players'].values())

    if all_answered:
        # Reset "answered" for next round
        for player in lobbies[room]['players'].values():
            player['answered'] = False

        # Move to next question
        if lobbies[room]['questions']:
            next_question = lobbies[room]['questions'].pop(0)

            # BEFORE emitting next question, set correct_zone
            correct_index = next_question['answers'].index(next_question['solution'])

            canvas_width = 1024  # match your frontend!
            canvas_height = 576

            rect_width = canvas_width * 0.4
            rect_height = canvas_height * 0.4

            if correct_index == 0:
                correct_zone = (0, 0, rect_width, rect_height)
            elif correct_index == 1:
                correct_zone = (canvas_width - rect_width, 0, rect_width, rect_height)
            elif correct_index == 2:
                correct_zone = (0, canvas_height - rect_height, rect_width, rect_height)
            elif correct_index == 3:
                correct_zone = (canvas_width - rect_width, canvas_height - rect_height, rect_width, rect_height)

            lobbies[room]['correct_zone'] = correct_zone

            socketio.emit('next_question', next_question, room=room)

        else:
            # No more questions, game over
            players = lobbies.get(room, {}).get('players', {})
            winner_sid = max(players, key=lambda sid: players[sid].get('score', 0))
            winner = players[winner_sid]

            socketio.emit('game_over', {
                'winnerName': winner['username'],
                'winnerScore': winner.get('score', 0)
            }, room=room)

    # Update player scores
    player_scores = [
        {'username': player['username'], 'score': player.get('score', 0)}
        for player in lobbies[room]['players'].values()
    ]
    socketio.emit('update_player_scores', player_scores, room=room)

@socketio.on('update_score')
def handle_update_score(data):
    sid = request.sid
    room = player_data.get(sid, {}).get('room')
    score = data.get('score', 0)

    if room and sid in lobbies.get(room, {}).get('players', {}):
        lobbies[room]['players'][sid]['score'] = score

        # After updating, broadcast new scores
        player_scores = sorted(
            [
                {'username': player['username'], 'score': player.get('score', 0)}
                for player in lobbies[room]['players'].values()
            ],
            key=lambda p: p['score'],
            reverse=True
        )

        socketio.emit('update_player_scores', player_scores, room=room)

# --- Set up avatar uploads

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Lobby
lobbies = {}

# https://opentdb.com/api.php?amount=${amount}&category=18&difficulty=medium&type=multiple
def fetch_trivia_questions(amount=10):
    response = requests.get(f"https://opentdb.com/api.php?amount={amount}&category=18&difficulty=medium&type=multiple")
    data = response.json()
    questions = []

    for result in data['results']:
        question = result['question']
        correct = result['correct_answer']
        incorrect = result['incorrect_answers']
        all_answers = incorrect + [correct]

        # Randomize answers
        random.shuffle(all_answers)

        questions.append({
            'question': question,
            'answers': all_answers,
            'solution': correct
        })
    return questions

@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    join_room(room)

    if room not in lobbies:
        lobbies[room] = {'players': {}, 'questions': []}

    username = player_data[request.sid].get('username', 'Guest')
    lobbies[room]['players'][request.sid] = {'username': username, 'ready': False}

    player_data[request.sid]['room'] = room

    emit('update_lobby', lobbies[room]['players'], room=room)

@socketio.on('player_ready')
def handle_player_ready(data):
    room = data['room']
    lobbies[room]['players'][request.sid]['ready'] = True

    players = lobbies[room]['players']
    total_players = len(players)
    ready_players = sum(1 for p in players.values() if p['ready'])

    if ready_players / total_players >= 0.5:
        if not lobbies[room]['questions']:
            lobbies[room]['questions'] = fetch_trivia_questions()
        socketio.emit('start_game', {'questions': lobbies[room]['questions']}, room=room)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    room = player_data.get(sid, {}).get('room')

    if room and room in lobbies and sid in lobbies[room]['players']:
        del lobbies[room]['players'][sid]

        # Optional: broadcast updated lobby
        emit('update_lobby', lobbies[room]['players'], room=room)

        # Clean up empty rooms
        if not lobbies[room]['players']:
            del lobbies[room]

    player_data.pop(sid, None)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, allow_unsafe_werkzeug=True, debug=False)