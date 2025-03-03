# Import all blueprint modules
from routes.main_routes import main_bp
from routes.deck import deck_bp
from routes.flashcard_routes import flashcard_bp
from routes.flashcard_generation_routes import generation_bp
from routes.flashcard_stats_routes import stats_bp
from routes.flashcard_import_routes import import_bp

# Register blueprints function
def register_blueprints(app):
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(deck_bp, url_prefix='/deck')
    app.register_blueprint(flashcard_bp, url_prefix='/flashcard')
    app.register_blueprint(generation_bp, url_prefix='/generation')
    app.register_blueprint(stats_bp, url_prefix='/stats')
    app.register_blueprint(import_bp, url_prefix='/import')
