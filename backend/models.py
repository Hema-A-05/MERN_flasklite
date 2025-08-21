import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
client = MongoClient(os.environ.get('MONGO_URI'))
db = client.mern_like_app

# Collections
users_collection = db.users
agents_collection = db.agents
tasks_collection = db.tasks