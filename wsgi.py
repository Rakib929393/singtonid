import sys
import os

# Path to your project folder
project_home = '/home/nayeemmodz/mysite'  # Replace with your actual PythonAnywhere username and folder name
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Import your Flask app
from app import app as application  # 'app' is the name of the Flask app in app.py
