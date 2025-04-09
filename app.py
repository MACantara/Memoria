from flask import Flask, jsonify
import json
import os
from models import db
from config import Config
from routes import register_blueprints
from google import genai
from flask_login import LoginManager, login_required
from services.database_service import DatabaseService

def create_app(config_class=Config):
    # Ensure SQLite database directory exists before initializing the app
    config_class.ensure_sqlite_directory_exists()
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Set the database URI from the Config property method
    app.config['SQLALCHEMY_DATABASE_URI'] = config_class().SQLALCHEMY_DATABASE_URI
    
    # Initialize database using the service
    DatabaseService.init_db(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
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
    
    # Route for database synchronization
    @app.route('/api/sync-databases', methods=['POST'])
    @login_required
    def sync_databases_route():
        """API endpoint to trigger database synchronization"""
        try:
            # Only allow sync if both database types are configured
            config = Config()
            if not config.POSTGRES_URL:
                return jsonify({
                    'status': 'error',
                    'message': 'PostgreSQL database not configured'
                }), 400
                
            # Run synchronization using the service
            results = DatabaseService.sync_databases()
            return jsonify({
                'status': 'success',
                'results': results
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # Register blueprints using the centralized function
    register_blueprints(app)
    
    return app

app = create_app()

if __name__ == "__main__":
    try:
        print("Starting development server...")
        print(f"Access the application at: http://{Config.HOST}:{Config.PORT}")
        app.run(host=Config.HOST, port=Config.PORT)
    except Exception as e:
        print(f"Error starting development server: {e}")