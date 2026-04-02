#!/usr/bin/env python3
"""IndieGameDrop Pipeline Dashboard — Flask app factory and entry point."""

from flask import Flask

import config
from routes import register_blueprints


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        A fully configured Flask app with all blueprints registered.
    """
    app = Flask(__name__)

    # Load configuration into app.config
    app.config["DB_PATH"] = config.DB_PATH
    app.config["LOGS_DIR"] = config.LOGS_DIR
    app.config["CRON_STATUS_FILE"] = config.CRON_STATUS_FILE
    app.config["CRON_STATE_SCRIPT"] = config.CRON_STATE_SCRIPT
    app.config["PORT"] = config.PORT
    app.config["AUTO_REFRESH_SECONDS"] = config.AUTO_REFRESH_SECONDS
    app.config["PER_PAGE"] = config.PER_PAGE

    register_blueprints(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=False)
