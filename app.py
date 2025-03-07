from flask import Flask, g, request
from flask_login import LoginManager
import json
from models import db, User
from config import Config
from routes import register_blueprints
from google import genai
import os

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Initialize Gemini AI client if API key is available
    if Config.GEMINI_API_KEY:
        app.gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    @app.template_filter('fromjson')
    def fromjson_filter(value):
        """Convert JSON string to Python object, or return the value if already parsed"""
        if isinstance(value, (list, dict)):
            # Value is already a Python object, no need to parse
            return value
        
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            # Return empty list as fallback if parsing fails
            return []
    
    # Create database tables
    with app.app_context():
        db.create_all()

    # Register blueprints using the centralized function
    register_blueprints(app)
    
    # Register auth blueprint
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'])