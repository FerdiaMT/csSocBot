from flask import Flask
from threading import Thread
import socket
import logging

app = Flask('')

# Disable Flask's default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return "Bot is running!"

def find_free_port():
    """Find a free port to use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def run():
    port = find_free_port()
    print(f"Flask server running on port {port}")
    app.run(host='0.0.0.0', port=port, use_reloader=False, debug=False)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()