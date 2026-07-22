"""
extensions.py
Flask extension instances created at module scope so they can be imported
by models.py, routes.py, and init_db.py WITHOUT creating circular imports.

These extensions are bound to a specific Flask app later, inside
app.py's create_app() factory, via the init_app() calls.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

