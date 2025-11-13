from flask import Flask
from threading import Thread
import socket

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def run():
    port = find_free_port()
    print(f"Flask server starting on port {port}")
    app.run(host='0.0.0.0', port=port, use_reloader=False)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()