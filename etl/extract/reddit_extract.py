import os
import requests
from dotenv import load_dotenv
import json
from datetime import datetime
load_dotenv()
CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')

auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)

data = {
    'grant_type': 'password',
    'username': os.getenv('REDDIT_USERNAME'),
    'password': os.getenv('REDDIT_PASSWORD')
}