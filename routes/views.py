from flask import Blueprint, render_template
from flask_login import login_required

views_bp = Blueprint('views', __name__)

@views_bp.route('/imports')
@login_required
def imports_dashboard():
    """View all imports dashboard"""
    return render_template('imports.html')
