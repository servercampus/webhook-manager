from functools import wraps
from typing import Callable
from flask import session, redirect, url_for, request, flash
from werkzeug.security import check_password_hash
from storage import get_all_users


def verify_credentials(username: str, password: str) -> bool:
    users = get_all_users()
    stored_hash = users.get(username)
    if not stored_hash:
        return False
    return check_password_hash(stored_hash, password)


def login_required(view_func: Callable):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            # Remember target URL for redirect after login
            session["next"] = request.path
            flash("Bitte melde dich an.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


