from flask import Blueprint, render_template
from models import db, FlashcardDecks

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Only get top-level decks (for display in the grid)
    decks_for_grid = FlashcardDecks.query.filter_by(parent_deck_id=None).all()
    
    # Get ALL decks regardless of hierarchy for modals
    all_decks = FlashcardDecks.query.all()
    
    return render_template('index.html', decks=decks_for_grid, all_decks=all_decks)
