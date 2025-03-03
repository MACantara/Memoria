# Import all blueprint modules
from routes.main_routes import main_bp
from routes.deck import deck_bp
from routes.flashcard import register_flashcard_blueprints

# Register blueprints function
def register_blueprints(app):
    """Register all blueprints with the Flask application"""
    # Register main and deck blueprints directly
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(deck_bp, url_prefix='/deck')
    
    # Register all flashcard-related blueprints using the central registration function
    register_flashcard_blueprints(app)
