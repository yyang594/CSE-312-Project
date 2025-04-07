from pymongo import MongoClient
import os

def get_db():
    mongo_host = os.environ.get('MONGO_HOST', 'mongo')
    mongo_port = int(os.environ.get('MONGO_PORT', 27017))
    client = MongoClient(f'mongodb://{mongo_host}:{mongo_port}/')
    return client['testdb']
