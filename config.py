"""
config.py
Central configuration for the Network Device Management System.

Uses a base Config class plus environment-specific subclasses so the
app factory (app.py) can load the correct settings via a string key
(e.g. "development", "production", "testing").
"""

import os

# Absolute path to the project root directory (folder containing this file)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration with sensible defaults shared by all environments."""

    # Secret key used by Flask to sign session cookies and CSRF tokens.
    # In production this MUST be overridden via an environment variable.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me-in-production")

    # Path to the SQLite database file, stored at the project root.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    )

    # Disables a SQLAlchemy feature that tracks object modifications;
    # not needed here and adds unnecessary overhead.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-WTF CSRF protection is enabled by default; kept explicit for clarity.
    WTF_CSRF_ENABLED = True

    # How long a "remember me" login session persists, in seconds (7 days).
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 7

    # Number of seconds to allow a ping subprocess to run before timing out.
    PING_TIMEOUT = 2


class DevelopmentConfig(Config):
    """Configuration used during local development."""

    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set True temporarily to log all SQL statements


class ProductionConfig(Config):
    """Configuration used when deployed. Enforces a real secret key."""

    DEBUG = False

    def __init__(self):
        if os.environ.get("SECRET_KEY") is None:
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production."
            )


class TestingConfig(Config):
    """Configuration used by the automated test suite."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False  # Simplifies posting test forms without a CSRF token


# Maps a simple string key (used in app.py / FLASK_ENV) to its Config class.
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
