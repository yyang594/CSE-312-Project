from flask import Flask, jsonify, make_response, render_template
import database

app = Flask(__name__)
db = database.get_db()
collection = db['items']
@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
