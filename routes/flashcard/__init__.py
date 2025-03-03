from flask import Blueprint
from routes.flashcard.core_routes import flashcard_bp
from routes.flashcard.generation_routes import generation_bp
from routes.flashcard.stats_routes import stats_bp
from routes.flashcard.import_routes import import_bp

def register_flashcard_blueprints(app):
    """Register all flashcard-related blueprints with the application"""
    app.register_blueprint(flashcard_bp, url_prefix='/flashcard')
    app.register_blueprint(generation_bp, url_prefix='/generation')
    app.register_blueprint(stats_bp, url_prefix='/stats')
    app.register_blueprint(import_bp, url_prefix='/import')
