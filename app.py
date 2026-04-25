from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

# MOCK DATABASE 
keys_db = {
    "FZ-TEST-1111": {"status": "unused", "hwid": None},
    "FZ-TEST-2222": {"status": "unused", "hwid": None},
    "FZ-USED-9999": {"status": "used", "hwid": "SOME-OLD-HWID-STRING"}
}

@app.route('/verify-key', methods=['POST'])
def verify_key():
    # --- X-RAY VISION LOGGING ---
    print("\n" + "="*30)
    print(">>> NEW LOGIN ATTEMPT DETECTED <<<")
    
    # 1. Force parse the JSON to avoid format errors
    data = request.get_json(force=True, silent=True)
    print(f"[*] Raw Data Received: {data}")

    # If the app sent absolutely nothing or bad JSON
    if not data:
        print("[!] ERROR: Server received empty or invalid data format.")
        return jsonify({"status": "error", "message": "Invalid data format."}), 400

    # 2. Extract the variables
    user_key = data.get('key')
    user_hwid = data.get('hwid')
    
    print(f"[*] Extracted Key: '{user_key}'")
    print(f"[*] Extracted HWID: '{user_hwid}'")

    # Ensure they aren't blank
    if not user_key or not user_hwid:
        print("[!] ERROR: Missing key or HWID in the payload.")
        return jsonify({"status": "error", "message": "Missing key or HWID."}), 400

    # 3. Check if the key exists in our database
    if user_key not in keys_db:
        print("[!] ERROR: Key does not exist in database.")
        return jsonify({"status": "error", "message": "Invalid license key."}), 401

    key_info = keys_db[user_key]

    # 4. Handle an Unused Key
    if key_info["status"] == "unused":
        keys_db[user_key]["status"] = "used"
        keys_db[user_key]["hwid"] = user_hwid
        print(f"[SUCCESS] Key {user_key} activated and bound to HWID: {user_hwid}")
        return jsonify({"status": "success", "message": "Key activated and bound to device."}), 200

    # 5. Handle a Used Key
    elif key_info["status"] == "used":
        if key_info["hwid"] == user_hwid:
            print(f"[SUCCESS] Returning user logged in. HWID MATCH: {user_hwid}")
            return jsonify({"status": "success", "message": "Authentication successful."}), 200
        else:
            print(f"[WARNING] HWID MISMATCH! Key bound to {key_info['hwid']}, but {user_hwid} tried to use it.")
            return jsonify({"status": "error", "message": "Key is already bound to another device."}), 403

if __name__ == '__main__':
    print(">>> FROZEN FIRE APK BACKEND RUNNING <<<")
    print(">>> Synced with Telegram Bot Database <<<")
    
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)