from flask import Blueprint
from routes.deck.view_routes import deck_view_bp
from routes.deck.management_routes import deck_management_bp
from routes.deck.api_routes import deck_api_bp

deck_bp = Blueprint('deck', __name__)

# Register sub-blueprints
deck_bp.register_blueprint(deck_view_bp)
deck_bp.register_blueprint(deck_management_bp)
deck_bp.register_blueprint(deck_api_bp)
