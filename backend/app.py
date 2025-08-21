import os
import jwt
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')

# MongoDB connection
client = MongoClient(os.environ.get('MONGO_URI'))
db = client.mern_like_app
users_collection = db.users
agents_collection = db.agents
tasks_collection = db.tasks

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = users_collection.find_one({'_id': ObjectId(data['user_id'])})
        except:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# --- User Authentication ---
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = users_collection.find_one({'email': data['email']})

    if not user or not check_password_hash(user['password'], data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    token = jwt.encode({
        'user_id': str(user['_id']),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'token': token})

# --- Agent Management ---
@app.route('/agents', methods=['POST'])
@token_required
def add_agent(current_user):
    data = request.get_json()
    if not data or not data.get('name') or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing required fields'}), 400

    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_agent = {
        'name': data['name'],
        'email': data['email'],
        'mobile': data.get('mobile', ''),
        'password': hashed_password
    }
    agents_collection.insert_one(new_agent)
    return jsonify({'message': 'Agent added successfully!'}), 201

@app.route('/agents', methods=['GET'])
@token_required
def get_agents(current_user):
    agents = list(agents_collection.find({}, {'_id': 0, 'password': 0}))
    return jsonify(agents)

# --- CSV Upload and Distribution ---
@app.route('/upload-csv', methods=['POST'])
@token_required
def upload_csv(current_user):
    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        return jsonify({'message': 'Invalid file type. Only CSV, XLSX, and XLS are allowed'}), 400

    try:
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        # Validate columns
        if not all(col in df.columns for col in ['FirstName', 'Phone', 'Notes']):
            return jsonify({'message': 'CSV format is incorrect. Required columns: FirstName, Phone, Notes'}), 400

        tasks = df.to_dict('records')
        all_agents = list(agents_collection.find({}))
        num_agents = len(all_agents)
        num_tasks = len(tasks)

        if num_agents == 0:
            return jsonify({'message': 'No agents available to distribute tasks'}), 400

        tasks_per_agent = num_tasks // num_agents
        remaining_tasks = num_tasks % num_agents

        distributed_lists = {str(agent['_id']): [] for agent in all_agents}
        agent_ids = [str(agent['_id']) for agent in all_agents]

        task_index = 0
        for i in range(num_agents):
            agent_id = agent_ids[i]
            for _ in range(tasks_per_agent):
                distributed_lists[agent_id].append(tasks[task_index])
                task_index += 1

        for i in range(remaining_tasks):
            agent_id = agent_ids[i]
            distributed_lists[agent_id].append(tasks[task_index])
            task_index += 1

        # Save distributed lists to database
        for agent_id, agent_tasks in distributed_lists.items():
            tasks_collection.insert_one({
                'agent_id': ObjectId(agent_id),
                'tasks': agent_tasks,
                'upload_date': datetime.datetime.utcnow()
            })

        return jsonify({'message': 'Tasks distributed successfully', 'distributed_lists': distributed_lists}), 200

    except Exception as e:
        return jsonify({'message': f'Error processing file: {str(e)}'}), 500

@app.route('/distributed-lists', methods=['GET'])
@token_required
def get_distributed_lists(current_user):
    lists = tasks_collection.find({})
    all_lists = []
    for l in lists:
        all_lists.append({
            'agent_id': str(l['agent_id']),
            'tasks': l['tasks'],
            'upload_date': l['upload_date']
        })
    return jsonify(all_lists)

if __name__ == '__main__':
    app.run(debug=True, port=5000)