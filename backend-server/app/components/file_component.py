# backend/components/file_component.py
import uuid
import os
import json
from datetime import datetime
from .user_component import load_db, save_db
from werkzeug.utils import secure_filename

class FileComponent:
    def __init__(self):
        self.db = load_db()

    def register_encrypted_file(self, uploader, metadata, s3_key=None):
        # Internal UUID for security
        fid = str(uuid.uuid4())
        
        # User-friendly display name
        original_filename = metadata["orig_filename"]
        base_name = os.path.splitext(original_filename)[0]
        display_name = secure_filename(base_name)
        
        self.db["files"][fid] = {
            "id": fid,
            "display_name": display_name,  # ✅ Add this for user interface
            "user_friendly_id": display_name,  # ✅ For CLI display
            "uploader": uploader,
            "orig_filename": metadata["orig_filename"],
            "enc_file_path": metadata["enc_file_path"],
            "abe_ct": metadata["abe_ct"],
            "policy": metadata["policy"],
            "s3_key": s3_key,
            "created": datetime.utcnow().isoformat(),
            "context_policy": {},
        }
        save_db(self.db)
        return fid

    def get_file(self, fid):
        return self.db["files"].get(fid)

    def list_files(self):
        return list(self.db["files"].values())

    def set_s3_key(self, fid, s3_key):
        if fid not in self.db["files"]:
            return False
        self.db["files"][fid]["s3_key"] = s3_key
        save_db(self.db)
        return True

    def set_context_policy(self, fid, policy):
        if fid not in self.db["files"]:
            return False
        self.db["files"][fid]["context_policy"] = policy
        save_db(self.db)
        return True
