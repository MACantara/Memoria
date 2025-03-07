from flask import Blueprint, render_template, g, request
from models import db, FlashcardDecks
from routes.deck.utils import count_due_flashcards
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Filter decks based on user authentication
    if current_user.is_authenticated:
        # Get user's own decks + public decks for the grid
        decks_for_grid = FlashcardDecks.query.filter(
            (FlashcardDecks.user_id == current_user.id) | 
            (FlashcardDecks.user_id == None)
        ).filter_by(parent_deck_id=None).all()
        
        # Get ALL accessible decks regardless of hierarchy
        all_decks = FlashcardDecks.query.filter(
            (FlashcardDecks.user_id == current_user.id) | 
            (FlashcardDecks.user_id == None)
        ).all()
    else:
        # For anonymous users, only show public decks
        decks_for_grid = FlashcardDecks.query.filter_by(user_id=None, parent_deck_id=None).all()
        all_decks = FlashcardDecks.query.filter_by(user_id=None).all()
    
    # Make all_decks available to templates via g object for base.html to use
    g.all_decks = all_decks
    
    # Pass the count_due_flashcards function to the template
    return render_template('index.html', 
                          decks=decks_for_grid, 
                          all_decks=all_decks,
                          count_due_flashcards=count_due_flashcards)
