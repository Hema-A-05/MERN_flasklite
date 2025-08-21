import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')

from routes import *

if __name__ == '__main__':
    app.run(debug=True, port=5000)