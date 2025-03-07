from flask import Flask

def register_blueprints(app: Flask):
    """Register all blueprints with the application"""
    from routes.main_routes import main_bp
    app.register_blueprint(main_bp)
    
    # Register auth blueprint
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    # Register import routes
    from routes.import_routes import import_bp
    app.register_blueprint(import_bp)
    
    # Register search routes
    from routes.search_routes import search_bp
    app.register_blueprint(search_bp)
    
    # Register deck routes
    from routes.deck import deck_bp
    app.register_blueprint(deck_bp)
    
    # Register flashcard routes through their own registration function
    # This now includes stats routes which are registered as part of the flashcard blueprint
    from routes.flashcard import register_flashcard_blueprints
    register_flashcard_blueprints(app)
    
    # Remove the separate stats routes registration since they are now part of the flashcard package
    # from routes.stats import stats_bp  # <- This line causes the error
    # app.register_blueprint(stats_bp)  # <- This line is no longer needed