from flask import Blueprint, jsonify, request, current_app
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_current_time
from utils import count_due_flashcards
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

deck_api_bp = Blueprint('deck_api', __name__)

@deck_api_bp.route("/decks/tree")
@login_required
def get_deck_tree():
    """Get the complete deck hierarchy as a tree structure"""
    # Get top-level decks for current user
    root_decks = FlashcardDecks.query.filter_by(
        parent_deck_id=None,
        user_id=current_user.id
    ).all()
    
    # Build tree recursively
    result = []
    for deck in root_decks:
        result.append(build_deck_tree(deck))
    
    return jsonify(result)

def build_deck_tree(deck):
    """Helper function to build a deck tree structure recursively"""
    deck_dict = {
        'flashcard_deck_id': deck.flashcard_deck_id,
        'name': deck.name,
        'description': deck.description,
        'child_decks': []
    }
    
    for child in deck.child_decks:
        deck_dict['child_decks'].append(build_deck_tree(child))
    
    return deck_dict

@deck_api_bp.route("/decks")
@login_required
def get_decks_api():
    """Get all decks as a structured JSON for API use"""
    # Get top-level decks for current user
    root_decks = FlashcardDecks.query.filter_by(
        parent_deck_id=None,
        user_id=current_user.id
    ).all()
    
    result = []
    for deck in root_decks:
        result.append({
            "id": deck.flashcard_deck_id,
            "name": deck.name,
            "children": get_child_decks(deck.flashcard_deck_id)
        })
    
    return jsonify(result)

def get_child_decks(parent_id):
    """Helper function to recursively get child decks"""
    child_decks = FlashcardDecks.query.filter_by(parent_deck_id=parent_id).all()
    result = []
    
    for deck in child_decks:
        result.append({
            "id": deck.flashcard_deck_id,
            "name": deck.name,
            "children": get_child_decks(deck.flashcard_deck_id)
        })
    
    return result

@deck_api_bp.route("/list", methods=["GET"])
@login_required
def api_list_decks():
    """Get all decks as a flat list for API usage"""
    decks = FlashcardDecks.query.filter_by(
        user_id=current_user.id
    ).order_by(FlashcardDecks.name).all()
    result = []
    
    for deck in decks:
        result.append({
            'id': deck.flashcard_deck_id,
            'name': deck.name,
            'parent_id': deck.parent_deck_id,
            'flashcard_count': len(deck.flashcards) if deck.flashcards else 0
        })
    
    return jsonify(result)

@deck_api_bp.route("/due-counts", methods=["GET"])
@login_required
def get_due_counts():
    """Get due flashcard counts for all decks"""
    try:
        # Add debugging
        current_app.logger.info(f"Getting due counts for user {current_user.id}")
        
        # Get all decks for the current user
        decks = FlashcardDecks.query.filter_by(user_id=current_user.id).all()
        
        # Calculate due counts for each deck
        result = {}
        for deck in decks:
            deck_id = deck.flashcard_deck_id
            result[str(deck_id)] = count_due_flashcards(deck_id)
        
        current_app.logger.debug(f"Due counts result: {result}")
        return jsonify({
            "success": True,
            "counts": result
        })
    except Exception as e:
        current_app.logger.error(f"Error getting due counts: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@deck_api_bp.route("/due-count/<int:deck_id>")
@login_required
def get_due_count(deck_id):
    """Get the count of due flashcards for a specific deck"""
    try:
        # Check if deck exists and belongs to current user
        deck = FlashcardDecks.query.get_or_404(deck_id)
        
        if deck.user_id != current_user.id:
            return jsonify({
                "success": False,
                "error": "Unauthorized access"
            }), 403
        
        # Get due count for the deck
        due_count = count_due_flashcards(deck_id)
        
        return jsonify({
            "success": True,
            "deck_id": deck_id,
            "due_count": due_count
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@deck_api_bp.route('/toggle-public/<int:deck_id>', methods=['POST'])
@login_required
def toggle_public_deck(deck_id):
    """Toggle a deck's public/private status"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if user owns the deck
    if deck.user_id != current_user.id:
        return jsonify({"success": False, "error": "You don't have permission to modify this deck"}), 403
    
    try:
        # Use the toggle_public method to change the status
        is_public = deck.toggle_public()
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "is_public": is_public,
            "message": f"Deck is now {'public' if is_public else 'private'}"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@deck_api_bp.route('/import-deck/<int:deck_id>', methods=['POST'])
@login_required
def import_deck(deck_id):
    """Import a deck from another user"""
    # Get the source deck
    source_deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if the deck is public or belongs to the current user
    if not source_deck.is_public and source_deck.user_id != current_user.id:
        return jsonify({"success": False, "error": "This deck is private and cannot be imported"}), 403
    
    try:
        # Create a new deck for the current user
        new_deck = FlashcardDecks(
            name=f"{source_deck.name} (Imported)",
            description=source_deck.description,
            user_id=current_user.id
        )
        db.session.add(new_deck)
        db.session.flush()  # Get the new deck ID
        
        # Copy all flashcards from the source deck
        flashcards = Flashcards.query.filter_by(flashcard_deck_id=deck_id).all()
        
        for card in flashcards:
            # Create a new flashcard based on the original
            new_card = Flashcards(
                flashcard_deck_id=new_deck.flashcard_deck_id,
                question=card.question,
                correct_answer=card.correct_answer,
                incorrect_answers=card.incorrect_answers,
                state=0,  # Reset state to 'new'
                due_date=None  # Reset due date
            )
            db.session.add(new_card)
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Successfully imported {len(flashcards)} flashcards to your new deck",
            "deck_id": new_deck.flashcard_deck_id
        })
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Error importing deck: {str(e)}"}), 500
