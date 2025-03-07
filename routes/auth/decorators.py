from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user

def login_required_for_decks(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this feature', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
