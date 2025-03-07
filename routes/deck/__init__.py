from flask import Blueprint

deck_bp = Blueprint('deck', __name__, url_prefix='/deck')

# Import sub-blueprints
from routes.deck.view_routes import deck_view_bp
from routes.deck.api_routes import api_bp
from routes.deck.management_routes import management_bp

# Register sub-blueprints 
deck_bp.register_blueprint(deck_view_bp)
deck_bp.register_blueprint(api_bp, url_prefix='/api')
deck_bp.register_blueprint(management_bp)
