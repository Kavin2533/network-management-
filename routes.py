"""
routes.py
Route handlers, organized into two blueprints:
  - auth_bp:   login / logout / change password
  - main_bp:   dashboard, device CRUD, and the live ping endpoint

Blueprints are registered onto the app inside app.py's create_app().
"""

import platform
import socket
import subprocess
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    current_app,
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)
from sqlalchemy import or_, nullslast

from extensions import db
from models import User, Device
from forms import LoginForm, DeviceForm, ChangePasswordForm

auth_bp = Blueprint("auth", __name__)
main_bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handles user login. Redirects to the dashboard if already logged in."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            next_page = request.args.get("next")
            # Only honor `next` if it's a relative path, to prevent
            # open-redirect attacks via a crafted `?next=` query string.
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("main.dashboard"))
        flash("Invalid username or password.", "danger")

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Logs the current user out and redirects to the login page."""
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Lets the logged-in user change their own password."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash("Password updated successfully.", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("change_password.html", form=form)


# ---------------------------------------------------------------------------
# Main routes
# ---------------------------------------------------------------------------

@main_bp.route("/")
@login_required
def index():
    """Root URL just redirects to the dashboard."""
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Shows summary metric cards (total / online / offline / unknown devices)
    plus a short list of the most recently checked devices.
    """
    total = Device.query.count()
    online = Device.query.filter_by(status="Online").count()
    offline = Device.query.filter_by(status="Offline").count()
    unknown = Device.query.filter_by(status="Unknown").count()

    recent_devices = (
        Device.query.order_by(nullslast(Device.last_checked.desc()))
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        total=total,
        online=online,
        offline=offline,
        unknown=unknown,
        recent_devices=recent_devices,
    )


@main_bp.route("/devices")
@login_required
def device_list():
    """
    Shows all devices in a searchable table. Supports a `?q=` query string
    that matches against device name, IP address, or location.
    """
    query = request.args.get("q", "").strip()
    devices_query = Device.query

    if query:
        like_pattern = f"%{query}%"
        devices_query = devices_query.filter(
            or_(
                Device.device_name.ilike(like_pattern),
                Device.ip_address.ilike(like_pattern),
                Device.location.ilike(like_pattern),
            )
        )

    devices = devices_query.order_by(Device.device_name.asc()).all()
    return render_template("device_list.html", devices=devices, query=query)


@main_bp.route("/device/add", methods=["GET", "POST"])
@login_required
def device_add():
    """Creates a new device."""
    form = DeviceForm()
    if form.validate_on_submit():
        device = Device(
            device_name=form.device_name.data.strip(),
            ip_address=form.ip_address.data.strip(),
            device_type=form.device_type.data,
            vendor=form.vendor.data.strip(),
            location=form.location.data.strip(),
            service_name=form.service_name.data.strip() if form.service_name.data else None,
            service_port=form.service_port.data,
        )
        db.session.add(device)
        db.session.commit()
        flash(f'Device "{device.device_name}" added successfully.', "success")
        return redirect(url_for("main.device_list"))

    return render_template("device_form.html", form=form, mode="add")


@main_bp.route("/device/edit/<int:device_id>", methods=["GET", "POST"])
@login_required
def device_edit(device_id):
    """Edits an existing device."""
    device = Device.query.get_or_404(device_id)
    form = DeviceForm(obj=device, device_id=device.id)

    if form.validate_on_submit():
        device.device_name = form.device_name.data.strip()
        device.ip_address = form.ip_address.data.strip()
        device.device_type = form.device_type.data
        device.vendor = form.vendor.data.strip()
        device.location = form.location.data.strip()
        device.service_name = form.service_name.data.strip() if form.service_name.data else None
        device.service_port = form.service_port.data
        db.session.commit()
        flash(f'Device "{device.device_name}" updated successfully.', "success")
        return redirect(url_for("main.device_list"))

    return render_template("device_form.html", form=form, mode="edit", device=device)


@main_bp.route("/device/delete/<int:device_id>", methods=["POST"])
@login_required
def device_delete(device_id):
    """Deletes a device. POST-only to prevent accidental deletion via a GET link."""
    device = Device.query.get_or_404(device_id)
    name = device.device_name
    db.session.delete(device)
    db.session.commit()
    flash(f'Device "{name}" deleted.', "success")
    return redirect(url_for("main.device_list"))


# ---------------------------------------------------------------------------
# Service monitoring helpers
# ---------------------------------------------------------------------------

def check_service_port(host, port, timeout=2):
    """Returns True when a TCP connection to the host/port succeeds."""
    if not host or not port:
        return False

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


# ---------------------------------------------------------------------------
# Live status ping engine
# ---------------------------------------------------------------------------

def ping_host(ip_address, timeout=2):
    """
    Pings a single host using the OS's native `ping` utility and returns
    True if it responded, False otherwise.

    Uses subprocess with a fixed, non-shell argument list (no shell=True,
    no string interpolation into a shell command) so the ip_address value
    can never be used for command injection, even though it has already
    been validated as a strict IPv4 address at the form layer.
    """
    is_windows = platform.system().lower() == "windows"

    if is_windows:
        # -n 1  : send exactly 1 echo request
        # -w    : timeout in milliseconds
        command = ["ping", "-n", "1", "-w", str(timeout * 1000), ip_address]
    else:
        # -c 1  : send exactly 1 echo request
        # -W    : timeout in seconds (Linux); macOS uses -t, handled below
        if platform.system().lower() == "darwin":
            command = ["ping", "-c", "1", "-t", str(timeout), ip_address]
        else:
            command = ["ping", "-c", "1", "-W", str(timeout), ip_address]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + 2,  # hard safety cap above the ping tool's own timeout
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


@main_bp.route("/device/<int:device_id>/check-service", methods=["POST"])
@login_required
def device_service_check(device_id):
    """Checks a configured TCP service for this device and stores the result."""
    device = Device.query.get_or_404(device_id)

    if not device.service_port:
        return jsonify({"error": "No service port configured for this device."}), 400

    is_open = check_service_port(
        device.ip_address,
        device.service_port,
        timeout=current_app.config.get("PING_TIMEOUT", 2),
    )
    device.mark_service_status("Open" if is_open else "Closed")
    db.session.commit()

    return jsonify(
        {
            "id": device.id,
            "service_status": device.service_status,
            "last_service_check": device.last_service_check.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


@main_bp.route("/device/<int:device_id>/ping", methods=["POST"])
@login_required
def device_ping(device_id):
    """
    Pings a single device on demand and persists the resulting status.
    Returns JSON so the frontend (status_ping.js) can update the UI
    without a full page reload.
    """
    device = Device.query.get_or_404(device_id)

    is_online = ping_host(device.ip_address, timeout=current_app.config.get("PING_TIMEOUT", 2))
    device.mark_status("Online" if is_online else "Offline")
    db.session.commit()

    return jsonify(
        {
            "id": device.id,
            "status": device.status,
            "last_checked": device.last_checked.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


@main_bp.route("/devices/ping-all", methods=["POST"])
@login_required
def device_ping_all():
    """
    Pings every device in the database in sequence and returns the
    updated list as JSON. Used by the dashboard's "Refresh All" button.
    """
    devices = Device.query.all()
    results = []

    for device in devices:
        is_online = ping_host(device.ip_address, timeout=current_app.config.get("PING_TIMEOUT", 2))
        device.mark_status("Online" if is_online else "Offline")
        results.append(device.to_dict())

    db.session.commit()
    return jsonify({"results": results, "checked_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")})
