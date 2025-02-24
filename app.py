from flask import Flask
from dotenv import load_dotenv
import os
from models import db
from routes.main_routes import main_bp
from routes.deck_routes import deck_bp
from routes.flashcard_routes import flashcard_bp

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configure database
    db_url = os.getenv('POSTGRES_URL_NON_POOLING', '').replace('postgres://', 'postgresql://')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(deck_bp, url_prefix='/deck')
    app.register_blueprint(flashcard_bp, url_prefix='/flashcard')
    
    return app

app = create_app()

# Create tables if they don't exist
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    # Development configuration
    app.debug = True
    
    try:
        print("Starting development server...")
        print("Access the application at: http://localhost:5000")
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Error starting development server: {e}")