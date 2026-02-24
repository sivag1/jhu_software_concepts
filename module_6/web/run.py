"""Flask application entrypoint.

Binds to 0.0.0.0:8080 for container deployment.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
