"""
models.py
SQLAlchemy ORM models for the Network Device Management System.

Imports `db` from extensions.py. This avoids circular imports since
db is defined at module scope in extensions.py, separate from the
Flask app factory in app.py.
"""

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(UserMixin, db.Model):
    """
    Represents an application user (network administrator) who can log in
    to manage devices. UserMixin supplies the properties Flask-Login needs
    (is_authenticated, is_active, is_anonymous, get_id()).
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, raw_password):
        """Hashes and stores the given plaintext password. Never store plaintext."""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """Returns True if raw_password matches the stored hash."""
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.username}>"


class Device(db.Model):
    """
    Represents a single network device (router, switch, firewall, server,
    or access point) tracked by the system.
    """

    __tablename__ = "devices"

    # Allowed values for device_type. Enforced at the form layer (forms.py)
    # via a SelectField, and used here just for reference/documentation.
    DEVICE_TYPES = ["Router", "Switch", "Firewall", "Server", "Access Point"]

    # Allowed values for status. "Unknown" is the default until the first
    # ping check runs.
    STATUS_CHOICES = ["Online", "Offline", "Unknown"]

    id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), unique=True, nullable=False, index=True)
    device_type = db.Column(db.String(20), nullable=False)
    vendor = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(150), nullable=True)
    status = db.Column(db.String(10), nullable=False, default="Unknown")
    last_checked = db.Column(db.DateTime, nullable=True)
    service_name = db.Column(db.String(50), nullable=True)
    service_port = db.Column(db.Integer, nullable=True)
    service_status = db.Column(db.String(10), nullable=False, default="Unknown")
    last_service_check = db.Column(db.DateTime, nullable=True)

    def mark_status(self, status):
        """
        Updates the device's status and stamps the current UTC time as the
        last-checked timestamp. Used by the live ping engine (Module 6 logic).
        """
        self.status = status
        self.last_checked = datetime.utcnow()

    def mark_service_status(self, status):
        """Updates the service status and timestamps the last service check."""
        self.service_status = status
        self.last_service_check = datetime.utcnow()

    def to_dict(self):
        """
        Serializes the device to a plain dict, used by the JSON ping
        endpoint and any future API responses.
        """
        return {
            "id": self.id,
            "device_name": self.device_name,
            "ip_address": self.ip_address,
            "device_type": self.device_type,
            "vendor": self.vendor,
            "location": self.location,
            "status": self.status,
            "last_checked": self.last_checked.strftime("%Y-%m-%d %H:%M:%S")
            if self.last_checked
            else None,
            "service_name": self.service_name,
            "service_port": self.service_port,
            "service_status": self.service_status,
            "last_service_check": self.last_service_check.strftime("%Y-%m-%d %H:%M:%S")
            if self.last_service_check
            else None,
        }

    def __repr__(self):
        return f"<Device {self.device_name} ({self.ip_address})>"

