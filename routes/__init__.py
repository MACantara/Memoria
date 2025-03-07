from flask import Flask

def register_blueprints(app: Flask):
    """Register all application blueprints"""
    # Import blueprints
    from routes.main_routes import main_bp
    from routes.import_routes import import_bp
    from routes.deck.__init__ import deck_bp
    from routes.flashcard.__init__ import register_flashcard_blueprints
    from routes.search_routes import search_bp
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(import_bp)
    app.register_blueprint(deck_bp)
    app.register_blueprint(search_bp)
    
    # Register all flashcard blueprints
    register_flashcard_blueprints(app)