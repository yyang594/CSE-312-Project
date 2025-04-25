import database
from server import questions_collection
#db = database.get_db()
#users_collection = db['users']

print("USER COLLECTION")
for item in questions_collection.find():
    print(item)