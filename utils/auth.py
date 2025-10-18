
from functools import wraps
from flask import session, redirect, url_for, flash

def require_role(*roles):
    """Decorator to require any of the specified roles: 'admin', 'manager', 'support'."""
    def deco(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            r = session.get("role")
            if r not in roles:
                flash("Недостаточно прав", "warning")
                return redirect(url_for("auth.login"))
            return view(*args, **kwargs)
        return wrapper
    return deco

def has_role(role: str) -> bool:
    return session.get("role") == role

def role_in(*roles):
    return session.get("role") in roles
