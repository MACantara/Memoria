from flask import Flask
import json
from models import db
from config import Config
from routes.main_routes import main_bp
from routes.deck_routes import deck_bp
from routes.flashcard_routes import flashcard_bp
from routes.flashcard_generation_routes import generation_bp
from routes.flashcard_stats_routes import stats_bp
from routes.flashcard_import_routes import import_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    


    # Initialize database
    db.init_app(app)
    
    @app.template_filter('fromjson')
    def fromjson_filter(value):
        return json.loads(value)
    
    # Register blueprints
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(deck_bp, url_prefix='/deck')
    app.register_blueprint(flashcard_bp, url_prefix='/flashcard')
    app.register_blueprint(generation_bp, url_prefix='/generation')
    app.register_blueprint(stats_bp, url_prefix='/stats')
    app.register_blueprint(import_bp, url_prefix='/import')
    
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