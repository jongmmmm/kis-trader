from app import create_app
import os
import threading

app = create_app()

def run_http():
    http_app = create_app()
    http_app.run(host="0.0.0.0", port=6000, debug=False)

if __name__ == "__main__":
    cert = os.path.expanduser("~/certbot/config/live/pois2000.duckdns.org/fullchain.pem")
    key = os.path.expanduser("~/certbot/config/live/pois2000.duckdns.org/privkey.pem")

    # HTTP on port 6000
    http_thread = threading.Thread(target=run_http, daemon=True)
    http_thread.start()

    # HTTPS on port 6001
    if os.path.exists(cert) and os.path.exists(key):
        app.run(host="0.0.0.0", port=6001, debug=False, ssl_context=(cert, key))
    else:
        app.run(host="0.0.0.0", port=6001, debug=False)
