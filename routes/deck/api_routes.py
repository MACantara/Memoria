from flask import Blueprint, jsonify, request
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_current_time
from utils import count_due_flashcards
from flask_login import login_required, current_user

deck_api_bp = Blueprint('deck_api', __name__, url_prefix='/api')

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
        # Get all decks for the current user
        decks = FlashcardDecks.query.filter_by(user_id=current_user.id).all()
        
        # Calculate due counts for each deck
        result = {}
        for deck in decks:
            deck_id = deck.flashcard_deck_id
            result[str(deck_id)] = count_due_flashcards(deck_id)
        
        return jsonify({
            "success": True,
            "counts": result
        })
    except Exception as e:
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
