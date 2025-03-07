from flask import Blueprint
from routes.flashcard.core_routes import flashcard_bp
from routes.flashcard.generation_routes import generation_bp
from routes.flashcard.stats_routes import stats_bp

# Create a parent blueprint for all flashcard-related routes
flashcard_parent_bp = Blueprint('flashcard_parent', __name__, url_prefix='/flashcard')

# Register child blueprints
flashcard_parent_bp.register_blueprint(flashcard_bp)
flashcard_parent_bp.register_blueprint(generation_bp, url_prefix='/generation')
flashcard_parent_bp.register_blueprint(stats_bp, url_prefix='/stats')

# Add this function to maintain compatibility with routes/__init__.py
def register_flashcard_blueprints(app):
    """Register all flashcard-related blueprints with the application"""
    # Register the parent blueprint which contains all child blueprints
    app.register_blueprint(flashcard_parent_bp)
