# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
FILES_FILE = os.path.join(DATA_DIR, "files.json")

# FL threshold (tune if needed)
FL_ANOMALY_THRESHOLD = 0.2
