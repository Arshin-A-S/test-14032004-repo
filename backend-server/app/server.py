from flask import Flask, request, jsonify, send_file
from flask_cors import CORS # Import CORS
import os
import uuid
import json

from components.event_logger import log_event, get_events
from components.crypto_component import CryptoComponent
from components.s3_component import S3Component
from components.context_component import ContextComponent
from components.fl_component import FLComponent
from components.user_component import UserComponent
from components.file_component import FileComponent

app = Flask(__name__)
CORS(app)
# Configure S3
S3_BUCKET = "file-storage-00414"
S3_REGION = "eu-central-1"

# Components (now using Waters11)
crypto = CryptoComponent()
s3c = S3Component(S3_BUCKET, region_name=S3_REGION)
context_comp = ContextComponent()
fl_comp = FLComponent()
# fl_comp.client_train_and_report({
#     "location": {"chennai": 10, "mumbai": 5},
#     "device": {"laptop1": 8, "phone1": 3}
# })
user_comp = UserComponent()
file_comp = FileComponent()

UPLOAD_TEMP_DIR = "uploads"
os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)

# ---------------- Register ----------------
@app.route("/register", methods=["POST"])
def register():
    j = request.json
    username = j.get("username")
    attrs = j.get("attributes", [])
    location = j.get("location", "")

    ok, res = user_comp.register_user(username, attrs, location)
    if not ok:
        return jsonify({"success": False, "error": res}), 400

    # generate Waters11 CP-ABE SK for user
    try:
        crypto.load_master_keys()  # load PK/MSK
    except FileNotFoundError:
        crypto.setup(force=True)
        crypto.save_master_keys()

    try:
        abe_sk_b64 = crypto.generate_user_secret(attrs)
        user_comp.set_user_abe_sk(username, abe_sk_b64)
    except Exception as e:
        print("Warning: unable to generate Waters11 ABE SK:", e)
        abe_sk_b64 = None

    return jsonify({"success": True, "user": res, "abe_sk": abe_sk_b64})

# ---------------- Login (for CLI compat) ----------------
@app.route("/login", methods=["POST"])
def login():
    j = request.json
    username = j.get("username")
    user = user_comp.get_user(username)
    if not user:
        log_event(username, "LOGIN_FAIL", {"reason": "unknown user"})
        return jsonify({"ok": False, "error": "unknown user"}), 404
    log_event(username, "LOGIN_SUCCESS")
    return jsonify({"ok": True, "user": user})

# ---------------- Upload ----------------
@app.route("/upload", methods=["POST"])
def upload():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "file missing"}), 400

    f = request.files['file']
    username = request.form.get("username") or request.form.get("owner")
    if not username:
        return jsonify({"success": False, "error": "missing username/owner"}), 400

    policy = request.form.get("policy")
    if not policy:
        return jsonify({"success": False, "error": "policy is required"}), 400

    # Context policy fields
    context_policy_json = request.form.get("context_policy")
    allowed_locations = request.form.get("allowed_locations")
    required_device = request.form.get("required_device")
    required_department = request.form.get("required_department")
    time_window_json = request.form.get("time_window")

    fname = f.filename
    local_path = os.path.join(UPLOAD_TEMP_DIR, f"{uuid.uuid4()}_{fname}")
    f.save(local_path)

    # Encrypt file with Waters11 CP-ABE
    try:
        crypto.load_master_keys()
        meta = crypto.encrypt_file_hybrid(local_path, policy)
    except Exception as e:
        print(f"Waters11 encryption failed: {e}")
        return jsonify({"success": False, "error": f"encryption failed: {str(e)}"}), 500

    # ✅ BACK TO S3 UPLOAD (using real credentials)
    s3_key = f"enc/{uuid.uuid4()}_{fname}.enc"
    if not s3c.upload_file(meta["enc_file_path"], s3_key):
        return jsonify({"success": False, "error": "s3 upload failed"}), 500

    # Register in database
    fid = file_comp.register_encrypted_file(username, meta, s3_key=s3_key)

    # Handle context policies
    applied_policy = None
    if context_policy_json:
        try:
            cp = json.loads(context_policy_json)
            applied_policy = cp
            context_comp.add_policy(fid, cp)
            file_comp.set_context_policy(fid, cp)
        except Exception as e:
            print("Invalid context policy:", e)

    if not applied_policy:
        cp = {}
        if allowed_locations:
            cp["allowed_locations"] = [x.strip() for x in allowed_locations.split(",") if x.strip()]
        if required_device:
            cp["allowed_devices"] = [required_device]
        if time_window_json:
            try:
                tw = json.loads(time_window_json)
                cp["time_window"] = tw
            except Exception as e:
                print("Invalid time_window JSON:", e)

        if cp:
            context_comp.add_policy(fid, cp)
            file_comp.set_context_policy(fid, cp)

    # Clean up local encrypted file after S3 upload
    try:
        os.remove(meta["enc_file_path"])
        os.remove(local_path)  # Also remove original temp file
    except Exception:
        pass

    log_event(username, "UPLOAD_SUCCESS", {"file_id": fid, "s3_key": s3_key})
    return jsonify({"success": True, "file_id": fid, "s3_key": s3_key})


# ---------------- List ----------------
@app.route("/list_files", methods=["GET"])
def list_files():
    return jsonify({"ok": True, "files": file_comp.list_files()})

# Alias for CLI
@app.route("/list", methods=["GET"])
def list_files_alias():
    return list_files()

# ---------------- Download ----------------
@app.route("/download", methods=["POST"])
def download():
    j = request.json
    username = j.get("username")
    fid = j.get("file_id")
    context = j.get("context") or j.get("user_context") or {}

    user = user_comp.get_user(username)
    if not user:
        return jsonify({"success": False, "error": "unknown user"}), 404

    fmeta = file_comp.get_file(fid)
    if not fmeta:
        return jsonify({"success": False, "error": "unknown file"}), 404

    # Normalize device key
    if "device" in context and "device_id" not in context:
        context["device_id"] = context["device"]

    # Context-aware access control
    if not context_comp.check_access(fid, context):
        return jsonify({"success": False, "error": "context policy denied"}), 403

    # FL anomaly check
    score = fl_comp.score_access(context)
    # Use the trained threshold from the new model
    if "decision" in fl_comp.model and "threshold" in fl_comp.model["decision"]:
        threshold = fl_comp.model["decision"]["threshold"]
    else:
        # Fallback to old format
        threshold = fl_comp.model.get("global_threshold", 0.6)
    #threshold = 1.5  # Temporarily disable FL checks
    if score >= threshold:
        log_event(username, "DOWNLOAD_FLAGGED", {"file_id": fid, "score": score})
        return jsonify({"success": False, "error": "access flagged", "score": score}), 403


    # ✅ BACK TO S3 DOWNLOAD
    s3_key = fmeta.get("s3_key")
    if not s3_key:
        return jsonify({"success": False, "error": "file not in s3"}), 500

    # Download encrypted file from S3
    local_tmp = os.path.join(UPLOAD_TEMP_DIR, f"dl_{uuid.uuid4()}.enc")
    if not s3c.download_file(s3_key, local_tmp):
        return jsonify({"success": False, "error": "s3 download failed"}), 500

    # Prepare meta for Waters11 decryption
    encrypted_meta = {
        "orig_filename": fmeta["orig_filename"],
        "enc_file_path": local_tmp,
        "abe_ct": fmeta["abe_ct"],
        "policy": fmeta["policy"],
    }

    abe_sk_b64 = user.get("abe_sk")
    if not abe_sk_b64:
        return jsonify({"success": False, "error": "user has no Waters11 abe key"}), 500

    try:
        crypto.load_master_keys()
        dec_path = crypto.decrypt_file_hybrid(encrypted_meta, abe_sk_b64)
    except Exception as e:
        return jsonify({"success": False, "error": f"Waters11 decryption failed: {e}"}), 500

    # Clean up temporary downloaded file
    try:
        os.remove(local_tmp)
    except Exception:
        pass
    log_event(username, "DOWNLOAD_SUCCESS", {"file_id": fid})
    return send_file(dec_path, as_attachment=True, download_name=fmeta["orig_filename"])

@app.route("/api/events", methods=["GET"])
def list_events():
    events = get_events()
    # We can also add anomaly detection information here
    for event in events:
        # Simple rule: failed logins are anomalies
        if event['action'] == 'LOGIN_FAIL' or event['action'] == 'DOWNLOAD_FLAGGED':
            event['is_anomaly'] = True
        else:
            event['is_anomaly'] = False
    return jsonify({"success": True, "events": events})
    
# ✅ ADD THIS CRITICAL CODE TO START THE SERVER
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
