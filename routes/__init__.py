from flask import Flask

def register_blueprints(app: Flask):
    """Register all application blueprints"""
    # Import blueprints
    from routes.main_routes import main_bp
    from routes.import_routes import import_bp
    from routes.deck.__init__ import deck_bp
    from routes.flashcard.__init__ import register_flashcard_blueprints
    from routes.search_routes import search_bp
    from routes.auth_routes import auth_bp
    from routes.learning.__init__ import register_learning_blueprint
    from routes.user import user_bp
    from routes.views import views_bp
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(import_bp)
    app.register_blueprint(deck_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(views_bp)
    
    
    # Register all flashcard blueprints
    register_flashcard_blueprints(app)
    register_learning_blueprint(app)