from app import create_app

app = create_app()

if __name__ == "__main__":
    import os
    cert = os.path.expanduser("~/certbot/config/live/pois2000.duckdns.org/fullchain.pem")
    key = os.path.expanduser("~/certbot/config/live/pois2000.duckdns.org/privkey.pem")
    if os.path.exists(cert) and os.path.exists(key):
        app.run(host="0.0.0.0", port=6001, debug=False, ssl_context=(cert, key))
    else:
        app.run(host="0.0.0.0", port=6001, debug=False)
