from flask import Blueprint

user_bp = Blueprint('user', __name__, url_prefix='/user')

# Import routes to register them with the blueprint
from routes.user.view_routes import *
