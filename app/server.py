from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length, EqualTo, Regexp


import requests
import random
import database
import logging
import traceback
import os
from html import escape
import secrets
import hashlib
import bcrypt
import uuid

# --- Setup Logging ---

LOG_DIR = '/logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'app.log'),
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Separate logger for raw requests/responses (full.log)
full_log_path = os.path.join(LOG_DIR, 'full.log')
full_logger = logging.getLogger('full')
full_logger.setLevel(logging.INFO)
full_logger.propagate = False  # Prevents writing to app.log

full_handler = logging.FileHandler(full_log_path)
full_handler.setLevel(logging.INFO)
full_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
full_logger.addHandler(full_handler)

def scrub_headers(headers):
   scrubbed = {}
   for key, value in headers.items():
       lower_key = key.lower()
       if lower_key in ['authorization', 'x-auth-token']:
           continue  # remove completely

       if lower_key == 'cookie':
           # remove cookies containing 'auth_token' or 'session'
           cookie_parts = value.split('; ')
           safe_cookies = [part for part in cookie_parts if not any(k in part.lower() for k in ['auth_token', 'session'])]
           value = '; '.join(safe_cookies)

       scrubbed[key] = value
   return scrubbed
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

       if not user:
           logging.info(f"Login attempt failed: username '{username}' does not exist")
           return jsonify({"success": False, "message": "Invalid credentials."}), 401
       if not bcrypt.checkpw(password.encode(), user["password"]):
           logging.info(f"Login attempt failed: incorrect password for username '{username}'")
           return jsonify({"success": False, "message": "Invalid credentials."}), 401

       logging.info(f"Login successful for username '{username}'")

       token = secrets.token_hex(32)
       token_hash = hashlib.sha256(token.encode()).hexdigest()
       users_collection.update_one({"username": username}, {"$set": {"auth_token": token_hash}})


       response = make_response(redirect(url_for('home')))
       response.set_cookie("username", username, httponly=True, secure=True, samesite='Strict', max_age=3600)
       response.set_cookie("auth_token", token, httponly=True, secure=True, samesite='Strict', max_age=3600)
       return response
   return render_template('login.html', form=form)

@app.route('/leaderboard', methods=['GET', 'POST'])
def leaderboard():
    if request.method == 'POST':
        data = request.get_json()
        print("Received data:", data, flush=True)

        doesPlayerExist = users_collection.find_one({"username": data["player"]})

        if('auth_token' in request.cookies and doesPlayerExist):
            if(leaderboard_collection.find_one({"player": data["player"]})):
                #Player exists
                leaderboard_collection.update_one({"player": data["player"]},
                                                  {"$inc": {"wins": 1,
                                                            "correct": data["correct"]}})
            else:
                #Player doesn't exist
                toInsert = {
                    "player": data["player"],
                    "wins": 1,
                    "correct": data["correct"]
                }
                leaderboard_collection.insert_one(toInsert)

    return render_template('leaderboard.html')

@app.route('/getInfo', methods = ['GET'])
def getInfo():
    #Get leaderboard info

    print("CONTENTS OF DATABASE:", flush=True)
    data = list(leaderboard_collection.find({}, {"_id": 0}))  # exclude _id if not needed
    print(data, flush=True)
    return jsonify(data)

@app.route('/stats')
def stats():
    auth_token = request.cookies.get('auth_token')
    username = "Guest"
    stats = {"answers_correct": 0, "games_won": 0, "max_score": 0}

    if auth_token:
        token_hash = hashlib.sha256(auth_token.encode()).hexdigest()
        user = users_collection.find_one({"auth_token": token_hash})
        if user:
            username = user['username']
            stats = {
                "answers_correct": user.get("answers_correct", 0),
                "games_won": user.get("games_won", 0),
                "max_score": user.get("max_score", 0)
            }

    return render_template("stats.html", username=username, stats=stats)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        username = escape(form.username.data)
        password = form.password.data
        confirm_password = form.confirm_password.data

        if users_collection.find_one({"username": username}):
            logging.info(f"Registration attempt failed: username '{username}' already taken")
            return jsonify({"success": False, "message": "Username already taken."}), 400

        if password != confirm_password:
            logging.info(f"Registration attempt failed: passwords did not match for username '{username}'")
            return jsonify({"success": False, "message": "Passwords do not match."}), 400

        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        users_collection.insert_one({
            "username": username,
            "password": hashed_pw,
            "answers_correct": 0,
            "games_won": 0,
            "max_score": 0,
            "profile_image": "/static/uploads/default.jpg"
        })
        logging.info(f"Registration successful for username '{username}'")
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
def attach_username():
   request.username = "Guest"
   auth_token = request.cookies.get('auth_token')
   if auth_token:
       token_hash = hashlib.sha256(auth_token.encode()).hexdigest()
       user = users_collection.find_one({"auth_token": token_hash})
       if user:
           request.username = user['username']

@app.after_request
def log_all_requests(response):
   try:
       forwarded_for = request.headers.get('X-Forwarded-For', None)
       ip = forwarded_for.split(',')[0].strip() if forwarded_for else request.remote_addr
       username = getattr(request, 'username', 'Guest')
       method = request.method
       path = request.path
       status_code = response.status_code
       logging.info(f"{ip} {username} {method} {path} {status_code}")

       # --- FULL raw logs: to full.log only ---
       if not path.startswith('/static'):
           headers = scrub_headers(dict(request.headers))
           content_type = request.content_type or ""

           # 🚫 Do NOT log body for POST /login or POST /register
           skip_body = method == 'POST' and path in ['/login', '/register']

           if skip_body:
               full_logger.info(f"REQUEST: {method} {path}\nHeaders: {headers}\n")
           else:
               if 'multipart/form-data' in content_type or 'application/octet-stream' in content_type:
                   request_body = '[non-text content skipped]'
               else:
                   request_body = request.get_data(as_text=True)[:2048]

               full_logger.info(f"REQUEST: {method} {path}\nHeaders: {headers}\nBody: {request_body}\n")

           # --- Log response ---
           resp_content_type = response.content_type or ""
           response_headers = scrub_headers(dict(response.headers))
           if response.direct_passthrough or 'application/octet-stream' in resp_content_type:
               response_body = '[non-text content skipped]'
           else:
               response_body = response.get_data(as_text=True)[:2048]

           full_logger.info(f"RESPONSE: {response.status}\nHeaders: {response_headers}\nBody: {response_body}\n")

   except Exception as e:
       logging.error(f"Failed to log request/response: {e}")

   return response

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

    username = user.get('username', 'Guest')
    logging.info(f"[WS] {username} moved: {data}")

    data.update({
        'name': user.get('username', 'Guest'),
        'profile_picture': user.get('profile_image', '/static/default-pfp.jpg'),
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
                'name': pdata.get('username', 'Guest'),
                'profile_picture': pdata.get('profile_image', '/static/default-pfp.jpg')
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
            'name': pdata.get('username', 'Guest'),
            'profile_picture': pdata.get('profile_image', '/static/default-pfp.jpg')
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

UPLOAD_DIR = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.config['UPLOAD_DIR'] = UPLOAD_DIR

@app.route('/profile')
def profile():
    username = request.cookies.get("username")
    user = users_collection.find_one({"username": username})
    if not user:
        return redirect(url_for("home"))
    
    profile_pic = user.get("profile_picture", "/static/default-pfp.jpg")

    return render_template("profile.html", user_pfp=profile_pic)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {"jpg", "png", "jpeg"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/profile/upload", methods=["POST"])
def upload_profile_pic():
    file = request.files["file"]

    if file.filename == "":
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{file_extension}"  

        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)

        # Update user profile picture in the database
        username = request.cookies.get("username")
        if username:
            users_collection.update_one(
                {"username": username},
                {"$set": {"profile_picture": f"/static/uploads/{filename}"}}
            )

            return jsonify({
                'status': 'ok',
                'message': 'Profile picture updated successfully!',
                'profile_picture': f"/static/uploads/{filename}"
            }), 200

    return jsonify({'status': 'error', 'message': 'Invalid upload'}), 400

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

    sid = request.sid
    username = player_data.get(sid, {}).get('username', 'Guest')
    lobbies[room]['players'][request.sid] = {'username': username, 'ready': False}
    logging.info(f"[WS] {username} joined room {room} (sid={sid})")

    username = player_data.get(request.sid, {}).get('username', 'Guest')
    user = users_collection.find_one({"username": username})
    profile_picture = user.get('profile_picture', '/static/default-pfp.jpg') if user else '/static/default-pfp.jpg'

    player_data[request.sid]['room'] = room
    player_data[request.sid]['profile_image'] = profile_picture

    lobbies[room]['players'][request.sid] = {
        'username': username,
        'ready': False,
        'profile_picture': profile_picture
    }

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
        socketio.emit('start_game', {}, room=room)  # only tell clients "game starting"

        handle_request_next_question({'room': room})

@socketio.on('game_result')
def handle_game_result(data):
    auth_token = request.cookies.get('auth_token')
    if not auth_token:
        return
    token_hash = hashlib.sha256(auth_token.encode()).hexdigest()
    user = users_collection.find_one({"auth_token": token_hash})
    if not user:
        return
    # Extract stats
    correct = int(data.get('correctAnswers', 0))
    score = int(data.get('score', 0))
    did_win = bool(data.get('didWin', False))
    updates = {
        "$inc": {
            "answers_correct": correct,
            "games_won": 1 if did_win else 0
        },
        "$max": {
            "max_score": score
        }
    }
    users_collection.update_one({"_id": user['_id']}, updates)

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

@app.errorhandler(Exception)
def handle_exception(e):
   # Log full traceback
   logging.error(f"Unhandled Exception: {e}\n{traceback.format_exc()}")

   # Optionally, return a generic error message
   return "Internal Server Error", 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, allow_unsafe_werkzeug=True, debug=False)