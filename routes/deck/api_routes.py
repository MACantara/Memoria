from flask import Blueprint, jsonify
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import get_current_time
from routes.deck.utils import count_due_flashcards

deck_api_bp = Blueprint('deck_api', __name__)

@deck_api_bp.route("/api/decks/tree")
def get_deck_tree():
    """Get the complete deck hierarchy as a tree structure"""
    # Get top-level decks
    root_decks = FlashcardDecks.query.filter_by(parent_deck_id=None).all()
    
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

@deck_api_bp.route("/api/decks")
def get_decks_api():
    """Get all decks as a structured JSON for API use"""
    # Get top-level decks
    root_decks = FlashcardDecks.query.filter_by(parent_deck_id=None).all()
    
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

@deck_api_bp.route("/api/list", methods=["GET"])
def api_list_decks():
    """Get all decks as a flat list for API usage"""
    decks = FlashcardDecks.query.order_by(FlashcardDecks.name).all()
    result = []
    
    for deck in decks:
        result.append({
            'id': deck.flashcard_deck_id,
            'name': deck.name,
            'parent_id': deck.parent_deck_id,
            'flashcard_count': len(deck.flashcards) if deck.flashcards else 0
        })
    
    return jsonify(result)

@deck_api_bp.route("/api/due-counts")
def get_due_counts():
    """Get counts of due flashcards for all decks"""
    current_time = get_current_time()
    decks = FlashcardDecks.query.all()
    result = {}
    
    for deck in decks:
        result[deck.flashcard_deck_id] = count_due_flashcards(deck.flashcard_deck_id, current_time)
    
    return jsonify(result)
