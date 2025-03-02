from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
from sqlalchemy.sql import func
from services.fsrs_scheduler import get_due_cards, get_current_time  # Add get_current_time import

deck_bp = Blueprint('deck', __name__)

@deck_bp.route("/<int:deck_id>")
def get_deck_flashcards(deck_id):
    """View deck structure and its contents"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    flashcards = Flashcards.query.filter_by(flashcard_deck_id=deck_id).all()
    
    # Count due flashcards for this deck (including sub-decks)
    current_time = get_current_time()
    due_count = count_due_flashcards(deck_id, current_time)
    
    return render_template("deck.html", deck=deck, flashcards=flashcards, due_count=due_count)

@deck_bp.route("/<int:deck_id>/study")
def study_deck(deck_id):
    """Study flashcards in this deck and all nested sub-decks using FSRS scheduling"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if we should only get due cards
    due_only = request.args.get('due_only', 'false').lower() == 'true'
    
    # Debug log
    print(f"Study request for deck {deck_id}: due_only={due_only}")
    
    # Get cards based on the due_only parameter
    if due_only:
        flashcards = get_due_cards(deck_id, due_only=True)
        print(f"Retrieved {len(flashcards)} due cards for study")
    else:
        flashcards = get_due_cards(deck_id, due_only=False)
        print(f"Retrieved {len(flashcards)} total cards for study")
    
    # Initialize FSRS state and due dates for any cards that need it
    if flashcards:
        current_time = get_current_time()
        for card in flashcards:
            # If card doesn't have FSRS state or state is None, initialize it
            if not card.fsrs_state or card.state is None:
                print(f"Initializing FSRS state for card {card.flashcard_id}")
                card.init_fsrs_state()
            
            # If card doesn't have a due date, make it due now
            if card.due_date is None:
                card.due_date = current_time
        
        db.session.commit()
    
    # Get parent deck information for each card to display subdeck names
    deck_info = {}
    for card in flashcards:
        if card.flashcard_deck_id != deck_id:  # This card is from a subdeck
            subdeck = FlashcardDecks.query.get(card.flashcard_deck_id)
            if subdeck:
                deck_info[card.flashcard_id] = {
                    'deck_id': subdeck.flashcard_deck_id,
                    'deck_name': subdeck.name
                }
    
    return render_template(
        "flashcards.html", 
        deck=deck, 
        flashcards=flashcards, 
        due_only=due_only,
        deck_info=deck_info
    )

@deck_bp.route("/create", methods=["POST"])
def create_deck():
    parent_deck_id = request.form.get("parent_deck_id")
    name = request.form.get("name", "New Deck")
    description = request.form.get("description", "")
    
    deck = FlashcardDecks(
        name=name,
        description=description,
        parent_deck_id=parent_deck_id
    )
    db.session.add(deck)
    db.session.commit()
    
    return jsonify({"success": True, "deck_id": deck.flashcard_deck_id})

@deck_bp.route("/rename/<int:deck_id>", methods=["PUT"])
def rename_deck(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
    try:
        data = request.json
        deck.name = data.get('name')
        deck.description = data.get('description')
        db.session.commit()
        return jsonify({"success": True, "message": "Deck renamed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@deck_bp.route("/delete/<int:deck_id>", methods=["DELETE"])
def delete_deck(deck_id):
    deck = FlashcardDecks.query.get_or_404(deck_id)
    try:
        # Create recursive CTE to find all sub-decks
        cte = db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.parent_deck_id == deck_id
        ).cte(name='sub_decks', recursive=True)

        cte = cte.union_all(
            db.session.query(
                FlashcardDecks.flashcard_deck_id.label('id')
            ).filter(
                FlashcardDecks.parent_deck_id == cte.c.id
            )
        )

        # Get all deck IDs including the parent
        all_deck_ids = [deck_id]  # Include the parent deck ID
        all_deck_ids.extend([row[0] for row in db.session.query(cte.c.id).all()])
        
        # Count sub-decks (excluding parent)
        sub_decks_count = len(all_deck_ids) - 1
        
        # Count flashcards from all levels
        flashcards_count = Flashcards.query.filter(
            Flashcards.flashcard_deck_id.in_(all_deck_ids)
        ).count()

        # Delete the deck (cascade will handle children)
        db.session.delete(deck)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": f"Deck deleted successfully along with {sub_decks_count} sub-deck{'s' if sub_decks_count != 1 else ''} "
                      f"and {flashcards_count} flashcard{'s' if flashcards_count != 1 else ''}"
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting deck: {str(e)}")  # Add logging
        return jsonify({"success": False, "error": str(e)}), 500

@deck_bp.route("/create_empty", methods=["POST"])
def create_empty_deck():
    try:
        data = request.json
        deck = FlashcardDecks(
            name=data.get('name', 'New Deck'),
            description=data.get('description', ''),
            parent_deck_id=None
        )
        db.session.add(deck)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "deck_id": deck.flashcard_deck_id,
            "message": "Empty deck created successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@deck_bp.route("/move/<int:deck_id>", methods=["PUT"])
def move_deck(deck_id):
    """Move a deck to a new parent deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    try:
        data = request.json
        new_parent_id = data.get('new_parent_id')
        
        # Validate the move
        if new_parent_id is not None:
            # Check that new parent exists
            new_parent = FlashcardDecks.query.get_or_404(new_parent_id)
            
            # Check for circular reference (can't move a deck into its own descendants)
            if is_descendant(new_parent_id, deck_id):
                return jsonify({"success": False, "error": "Cannot move a deck into its own subdeck"}), 400
            
            # Check if target is the same as current parent
            if deck.parent_deck_id == new_parent_id:
                return jsonify({"success": False, "error": "Deck is already in that location"}), 400
        elif deck.parent_deck_id is None:
            # Already at root level
            return jsonify({"success": False, "error": "Deck is already at root level"}), 400
        
        # Update the parent ID
        deck.parent_deck_id = new_parent_id
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Deck moved successfully"
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error moving deck: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@deck_bp.route("/api/decks/tree")
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

def is_descendant(potential_descendant_id, ancestor_id):
    """Check if a deck is a descendant of another deck"""
    if potential_descendant_id == ancestor_id:
        return True
        
    deck = FlashcardDecks.query.get(potential_descendant_id)
    if not deck:
        return False
    
    # If this deck has no parent, it can't be a descendant
    if deck.parent_deck_id is None:
        return False
        
    # Check if the parent is the ancestor we're looking for
    if deck.parent_deck_id == ancestor_id:
        return True
        
    # Recursively check the parent
    return is_descendant(deck.parent_deck_id, ancestor_id)

@deck_bp.route("/api/decks")
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
    child_decks = FlashcardDecks.query.filter_by(parent_id=parent_id).all()
    result = []
    
    for deck in child_decks:
        result.append({
            "id": deck.flashcard_deck_id,
            "name": deck.name,
            "children": get_child_decks(deck.flashcard_deck_id)
        })
    
    return result

# Add this new route to fetch all decks for the import modal
@deck_bp.route("/api/list", methods=["GET"])
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

# Add this new helper function
def count_due_flashcards(deck_id, current_time=None):
    """Count flashcards that are due for a deck and its sub-decks"""
    if current_time is None:
        current_time = get_current_time()
    
    # Create recursive CTE to find all decks including this one and its sub-decks
    cte = db.session.query(
        FlashcardDecks.flashcard_deck_id.label('id')
    ).filter(
        FlashcardDecks.flashcard_deck_id == deck_id
    ).cte(name='due_decks', recursive=True)

    cte = cte.union_all(
        db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.parent_deck_id == cte.c.id
        )
    )
    
    # Count cards that are due now
    due_count = Flashcards.query.filter(
        Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id)),
        (Flashcards.due_date <= current_time) | (Flashcards.due_date == None)
    ).count()
    
    return due_count

# Add this helper function for the deck listing
@deck_bp.route("/api/due-counts")
def get_due_counts():
    """Get counts of due flashcards for all decks"""
    current_time = get_current_time()
    decks = FlashcardDecks.query.all()
    result = {}
    
    for deck in decks:
        result[deck.flashcard_deck_id] = count_due_flashcards(deck.flashcard_deck_id, current_time)
    
    return jsonify(result)
