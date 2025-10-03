import json
import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'security_events.json')

def log_event(user, action, details=None):
    """Logs a security event to a JSON file."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            json.dump([], f)

    with open(LOG_FILE, 'r+') as f:
        events = json.load(f)
        
        new_event = {
            "id": len(events) + 1,
            "user": user,
            "action": action,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "details": details or {}
        }
        
        events.insert(0, new_event) # Add new events to the top
        f.seek(0)
        json.dump(events, f, indent=4)

def get_events(limit=50):
    """Retrieves the most recent security events."""
    if not os.path.exists(LOG_FILE):
        return []
        
    with open(LOG_FILE, 'r') as f:
        events = json.load(f)
        return events[:limit]