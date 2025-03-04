from flask import Flask
import json
from models import db
from config import Config
from routes import register_blueprints

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize database
    db.init_app(app)
    
    @app.template_filter('fromjson')
    def fromjson_filter(value):
        return json.loads(value)
    
    # Register blueprints using the centralized function
    register_blueprints(app)
    
    return app

app = create_app()

# Create tables if they don't exist
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    try:
        print("Starting development server...")
        print(f"Access the application at: http://{Config.HOST}:{Config.PORT}")
        app.run(host=Config.HOST, port=Config.PORT)
    except Exception as e:
        print(f"Error starting development server: {e}")