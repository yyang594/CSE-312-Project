from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length, EqualTo, Regexp

#from PIL import Image

import database
import logging
import os
from html import escape
import secrets
import hashlib
import bcrypt

# --- Setup Logging ---

LOG_DIR = '/logs'
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

@app.route('/submit_question', methods=['GET', 'POST'])
def submit_question():
    warning = ""
    if request.method == 'POST':
        questions = request.form.getlist('question[]')
        possibleAnswers = request.form.getlist('answer[]')
        correct_answer = request.form.getlist('correct_answer[]')

        if questions == []:
            warning = "Must have at least 1 question"
            return render_template('question_submission.html', warning=warning)
        if (possibleAnswers.count(correct_answer[0]) != 1):
            warning = "Correct answer either does not match any possible answers or matches too many answers"
            return render_template('question_submission.html', warning=warning)

        #Unfortunately the data's pretty ugly but questions/correct_answers is a list of questions/correct_answers
        #posibleAnswers is a list of all possible answers, each 4 answers correspond to a question in order
        #Note: edge cases: check for no correct answers
        #                  check how many answers are actually submitted
        #questions_collection.insert_one({"question": questions})

        #questions_collection.delete_many({})
        for i in range(len(questions)):
            toInsert = {
                "question": questions[i],
                "answers": [possibleAnswers[0],possibleAnswers[1],possibleAnswers[2],possibleAnswers[3]],
                "solution": correct_answer[i]
            }
            questions_collection.insert_one(toInsert)
        print("QUESTIONS")
        for item in questions_collection.find():
            print(item,flush=True)
        return redirect(url_for('home'))
        
    return render_template('question_submission.html', warning=warning)

@app.route('/test')
def test():
    print("USERS COLLECTION")
    info = []
    for item in users_collection.find():
        info.append(item)
    return jsonify(info)

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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_crop_image(image_path, size=(100, 100)):
    with Image.open(image_path) as img:

        img = img.convert("RGB")
        width, height = img.size
        min_dim = min(width, height)

        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
        right = (width + min_dim) / 2
        bottom = (height + min_dim) / 2
        img = img.crop((left, top, right, bottom))

        img = img.resize(size)
        img.save(image_path)

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['avatar']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        file.save(file_path)
        
        resize_crop_image(file_path)

        auth_token = request.cookies.get('auth_token')
        token_hash = hashlib.sha256(auth_token.encode()).hexdigest()
        user = users_collection.find_one({"auth_token": token_hash})
        
        if user:
            # Update the user's profile image URL in the database
            users_collection.update_one(
                {"auth_token": token_hash},
                {"$set": {"profile_image": f"/static/uploads/{filename}"}}
            )
        
        return jsonify({"message": "Avatar uploaded successfully", "image_url": f"/static/uploads/{filename}"}), 200
    
    return jsonify({"error": "Invalid file type"}), 400

#Lobby
rooms = {}

@app.route('/lobby')
def lobby():
    return render_template('lobby.html')


@socketio.on('join_room')
def on_join(data):
    room = data['room']
    join_room(room)
    if room not in rooms:
        rooms[room] = []
    rooms[room].append(request.sid)
    player_data[request.sid]['room'] = room
    emit('joined_room', {'room': room}, room=room)

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
    #DELETE DEBUG LATER
    socketio.run(app, host='0.0.0.0', port=8080, allow_unsafe_werkzeug=True, debug=False)