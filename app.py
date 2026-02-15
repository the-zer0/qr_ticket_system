from flask import Flask, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import qrcode
import os
from datetime import datetime
import secrets
import hashlib


app = Flask(__name__)

# ========== FIREBASE SETUP ==========
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Ensure static folder exists
if not os.path.exists("static"):
    os.makedirs("static")

# ========== ROUTES ==========

@app.route("/")
def home():
    return render_template("index.html")

# Admin page
@app.route("/admin")
def admin():
    return render_template("admin.html")

# Generate tickets
@app.route("/generate", methods=["POST"])
def generate():
    count = int(request.form["count"])
    salt = "thezer0"

    for _ in range(count):

        # Generate unique salted random ID
        while True:
            random_token = secrets.token_hex(8)
            raw_string = random_token + salt
            ticket_id = hashlib.sha256(raw_string.encode()).hexdigest()[:16]

            if not db.collection("tickets").document(ticket_id).get().exists:
                break

        # Save to Firestore
        db.collection("tickets").document(ticket_id).set({
            "status": "unused",
            "created_at": datetime.now()
        })

        # Generate QR
        img = qrcode.make(ticket_id)
        img.save(f"static/{ticket_id}.png")

    return f"{count} Random Secure Tickets Generated!"


# Scanner page
@app.route("/scanner")
def scanner():
    return render_template("scanner.html")

# Validate ticket
@app.route("/validate", methods=["POST"])
def validate():
    ticket_id = request.json["ticket_id"]

    ticket_ref = db.collection("tickets").document(ticket_id)
    ticket = ticket_ref.get()

    if ticket.exists:
        data = ticket.to_dict()

        if data["status"] == "unused":
            ticket_ref.update({
                "status": "used",
                "scanned_at": datetime.now()
            })
            return jsonify({"status": "valid"})
        else:
            return jsonify({"status": "already_used"})
    else:
        return jsonify({"status": "invalid"})

# Run locally
if __name__ == "__main__":
    app.run(debug=True)
