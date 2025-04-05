from flask import Blueprint
from routes.deck.view_routes import deck_view_bp
from routes.deck.management_routes import deck_management_bp
from routes.deck.api_routes import deck_api_bp
from routes.deck.bulk_api_routes import bulk_api_bp

# Create deck blueprint with the /deck prefix
deck_bp = Blueprint('deck', __name__, url_prefix='/deck')

# Register sub-blueprints
deck_bp.register_blueprint(deck_view_bp)  # view routes attached to /deck/
deck_bp.register_blueprint(deck_management_bp)  # management routes attached to /deck/
deck_bp.register_blueprint(deck_api_bp, url_prefix='/api')  # API routes explicitly attached to /deck/api/
deck_bp.register_blueprint(bulk_api_bp, url_prefix='/api')  # Bulk API routes attached to /deck/api/
