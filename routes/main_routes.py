from flask import Blueprint, render_template, g
from models import FlashcardDecks
from flask_login import current_user
from routes.deck.utils import count_due_flashcards

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
def index():
    """Main page - show decks for the current user or welcome page for logged out users"""
    if current_user.is_authenticated:
        # Only get top-level decks that belong to the current user
        decks = FlashcardDecks.query.filter_by(
            parent_deck_id=None, 
            user_id=current_user.id
        ).order_by(FlashcardDecks.name).all()
        
        # Make all decks available to templates
        g.all_decks = FlashcardDecks.query.filter_by(
            user_id=current_user.id
        ).all()
        
        return render_template('index.html', decks=decks, count_due_flashcards=count_due_flashcards)
    else:
        # Show welcome page for logged out users
        return render_template('index.html')
