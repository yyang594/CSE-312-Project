from flask import Flask, jsonify
import database

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
