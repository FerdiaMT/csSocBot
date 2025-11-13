from flask import Flask
from threading import Thread
import logging

app = Flask('')

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    try:
        app.run(host='0.0.0.0', port=8080, use_reloader=False, debug=False)
    except Exception as e:
        print(f"Flask server failed to start: {e}")

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()
    print("Flask thread started")
