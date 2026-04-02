"""Register all route blueprints with the Flask application."""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Import and register every route blueprint.

    Args:
        app: The Flask application instance.
    """
    from routes.overview import bp as overview_bp
    from routes.enrichment import bp as enrichment_bp
    from routes.snapshots import bp as snapshots_bp
    from routes.games import bp as games_bp
    from routes.scores import bp as scores_bp
    from routes.cron import bp as cron_bp
    from routes.logs import bp as logs_bp

    app.register_blueprint(overview_bp)
    app.register_blueprint(enrichment_bp)
    app.register_blueprint(snapshots_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(scores_bp)
    app.register_blueprint(cron_bp)
    app.register_blueprint(logs_bp)
