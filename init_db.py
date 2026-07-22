"""
init_db.py
One-time setup script: creates all database tables and seeds a default
admin user so you have something to log in with immediately.

Usage:
    python init_db.py
"""

from app import create_app
from extensions import db
from models import User

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"  # Change this immediately after first login!


def init_db():
    app = create_app()

    with app.app_context():
        db.create_all()
        print("Database tables created.")

        existing_admin = User.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first()
        if existing_admin:
            print(f'Admin user "{DEFAULT_ADMIN_USERNAME}" already exists. Skipping seed.')
            return

        admin = User(username=DEFAULT_ADMIN_USERNAME)
        admin.set_password(DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()

        print(f'Created default admin user: "{DEFAULT_ADMIN_USERNAME}" / "{DEFAULT_ADMIN_PASSWORD}"')
        print("IMPORTANT: Log in and change this password immediately (Change Password page).")


if __name__ == "__main__":
    init_db()
