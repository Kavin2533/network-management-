"""
forms.py
Flask-WTF form classes with full server-side validation.
"""

import ipaddress

from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional, ValidationError

from models import Device


def validate_ipv4(form, field):
    """
    Custom WTForms validator that ensures the submitted value is a
    syntactically valid IPv4 address, using the standard library's
    `ipaddress` module rather than a hand-rolled regex.
    """
    try:
        ipaddress.IPv4Address(field.data.strip())
    except ValueError:
        raise ValidationError("Please enter a valid IPv4 address (e.g. 192.168.1.1).")


class LoginForm(FlaskForm):
    """Login form for existing users."""

    username = StringField("Username", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")


class DeviceForm(FlaskForm):
    """
    Add/Edit form for a Device. Reused by both the "add device" and
    "edit device" views (Module 5), which is why it accepts an optional
    `device_id` in its constructor: when editing, we need to allow the
    device to keep its OWN ip_address without tripping the uniqueness
    check against itself.
    """

    device_name = StringField(
        "Device Name", validators=[DataRequired(), Length(max=100)]
    )
    ip_address = StringField(
        "IP Address", validators=[DataRequired(), validate_ipv4]
    )
    device_type = SelectField(
        "Device Type",
        choices=[(t, t) for t in Device.DEVICE_TYPES],
        validators=[DataRequired()],
    )
    vendor = StringField("Vendor", validators=[Length(max=100)])
    location = StringField("Location", validators=[Length(max=150)])
    service_name = StringField("Service Name", validators=[Optional(), Length(max=50)])
    service_port = IntegerField(
        "Service Port",
        validators=[Optional(), NumberRange(min=1, max=65535)],
    )
    submit = SubmitField("Save Device")

    def __init__(self, *args, device_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Stashed so validate_ip_address() below can exclude this device's
        # own current row when checking for duplicate IPs during an edit.
        self.device_id = device_id

    def validate_ip_address(self, field):
        """
        Rejects the submission with an inline field error if another
        device (a different id) already uses this IP address.
        """
        existing = Device.query.filter_by(ip_address=field.data.strip()).first()
        if existing and existing.id != self.device_id:
            raise ValidationError(
                "This IP address is already assigned to another device."
            )


class ChangePasswordForm(FlaskForm):
    """Lets a logged-in user change their own password."""

    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password", validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Change Password")

    def validate_current_password(self, field):
        """Rejects the submission if the supplied current password is wrong."""
        if not current_user.check_password(field.data):
            raise ValidationError("Current password is incorrect.")
