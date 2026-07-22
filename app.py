import os

from flask import Flask, render_template
from sqlalchemy import inspect, text

from config import config_by_name
from extensions import db, login_manager, csrf


def ensure_database_schema(app):
    """Adds new columns to existing SQLite tables when the app starts."""
    with app.app_context():
        inspector = inspect(db.engine)
        if "devices" not in inspector.get_table_names():
            db.create_all()
            return

        existing_columns = {column["name"] for column in inspector.get_columns("devices")}
        if "service_name" not in existing_columns:
            db.session.execute(text("ALTER TABLE devices ADD COLUMN service_name VARCHAR(50)"))
        if "service_port" not in existing_columns:
            db.session.execute(text("ALTER TABLE devices ADD COLUMN service_port INTEGER"))
        if "service_status" not in existing_columns:
            db.session.execute(text("ALTER TABLE devices ADD COLUMN service_status VARCHAR(10) DEFAULT 'Unknown'"))
        if "last_service_check" not in existing_columns:
            db.session.execute(text("ALTER TABLE devices ADD COLUMN last_service_check DATETIME"))
        db.session.commit()


def create_app(config_name=None):
    """
    Application factory.

    Args:
        config_name (str): One of "development", "production", "testing".
                            Defaults to the FLASK_ENV environment variable,
                            or "development" if that isn't set.

    Returns:
        Flask: A fully configured Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # --- Bind extensions to this specific app instance ---
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Where Flask-Login redirects unauthenticated users who hit a
    # @login_required route.
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    ensure_database_schema(app)
    with app.app_context():
        from models import User  # noqa: F401  (registers the model with SQLAlchemy)
        from routes import auth_bp, main_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)

        @login_manager.user_loader
        def load_user(user_id):
            """Tells Flask-Login how to reload a user object from the session."""
            return User.query.get(int(user_id))

    # --- Custom error handlers ---
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Ensure a failed transaction doesn't linger
        return render_template("500.html"), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config.get("DEBUG", True), host="0.0.0.0", port=5000)
