from flask import Blueprint

learning_bp = Blueprint('learning', __name__)

# Import routes from the separate route files
from routes.learning.session_routes import *
from routes.learning.section_routes import *
from routes.learning.interaction_routes import *

def register_learning_blueprint(app):
    """Register learning blueprint with the application"""
    app.register_blueprint(learning_bp, url_prefix='/learning')
