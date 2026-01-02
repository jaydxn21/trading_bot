# journal_server.py
from flask import Flask, request, jsonify
import csv
import threading
import json
import time
import os
from github import Github
from datetime import datetime


# ---------------- CONFIG ----------------
JOURNAL_FILE = "QuantumTrader_Journal.csv"
GITHUB_TOKEN = "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"
REPO_NAME = "jaydxn21/trading_bot"
REMOTE_PATH = "journals/quantum_journal.json"
SYNC_INTERVAL = 60
MAX_BUFFER = 500

# ---------------- SERVER ----------------
app = Flask(__name__)
journal_buffer = []

# ---------------- CSV INIT ----------------
if not os.path.exists(JOURNAL_FILE):
    with open(JOURNAL_FILE, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["time","symbol","event","ticket","volume","profit"]
        )
        writer.writeheader()

# ---------------- GITHUB SYNC ----------------
def push_to_github():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)

    while True:
        time.sleep(SYNC_INTERVAL)
        if not journal_buffer:
            continue

        payload = list(journal_buffer)
        journal_buffer.clear()

        content = json.dumps(payload, indent=2)

        try:
            file = repo.get_contents(REMOTE_PATH)
            repo.update_file(
                REMOTE_PATH,
                f"Journal update {datetime.utcnow().isoformat()}",
                content,
                file.sha
            )
            print(f"[{datetime.utcnow()}] Journal synced")
        except:
            repo.create_file(
                REMOTE_PATH,
                f"Initial journal {datetime.utcnow().isoformat()}",
                content
            )
            print(f"[{datetime.utcnow()}] Journal created")

# ---------------- JOURNAL ENDPOINT ----------------
@app.route("/journal", methods=["POST"])
def journal():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        with open(JOURNAL_FILE, "a", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["time","symbol","event","ticket","volume","profit"]
            )
            writer.writerow({
            "time": data.get("time", datetime.utcnow().isoformat()),
            "symbol": data.get("symbol",""),
            "event": data.get("event",""),
            "ticket": data.get("ticket",0),
            "profit": float(data.get("profit", 0))
        })

        journal_buffer.append(data)
        journal_buffer[:] = journal_buffer[-MAX_BUFFER:]

        return jsonify({"status":"ok"}), 200

    except Exception as e:
        return jsonify({"status":"error","message":str(e)}),500

# ---------------- MAIN ----------------
if __name__ == "__main__":
    t = threading.Thread(target=push_to_github, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=8085)
