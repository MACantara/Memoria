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
    """Import a deck from another user including all sub-decks and their flashcards"""
    # Get the source deck
    source_deck = FlashcardDecks.query.get_or_404(deck_id)
    
    # Check if the deck is public or belongs to the current user
    if not source_deck.is_public and source_deck.user_id != current_user.id:
        return jsonify({"success": False, "error": "This deck is private and cannot be imported"}), 403
    
    try:
        # Debug info
        print(f"Attempting to import deck {deck_id} ('{source_deck.name}') for user {current_user.id}")
        
        # Create a mapping to track which source deck ID maps to which new deck ID
        deck_mapping = {}
        
        # Create the main deck
        new_deck = FlashcardDecks(
            name=f"{source_deck.name} (Imported)",
            description=source_deck.description,
            parent_deck_id=None,  # Top-level deck
            user_id=current_user.id,
            is_public=False  # Always start as private
        )
        db.session.add(new_deck)
        db.session.flush()  # Get the new deck ID without committing yet
        
        # Remember the mapping from source deck ID to new deck ID
        deck_mapping[source_deck.flashcard_deck_id] = new_deck.flashcard_deck_id
        
        # First import flashcards for the main deck
        import_flashcards(source_deck.flashcard_deck_id, new_deck.flashcard_deck_id)
        
        # Then recursively import all child decks
        import_child_decks(source_deck, new_deck.flashcard_deck_id, deck_mapping)
        
        # Commit all changes
        db.session.commit()
        
        # Count total imported flashcards
        total_cards = count_imported_cards(new_deck.flashcard_deck_id)
        
        return jsonify({
            "success": True, 
            "message": f"Successfully imported deck with {total_cards} flashcards and {len(deck_mapping)-1} sub-decks",
            "deck_id": new_deck.flashcard_deck_id
        })
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error while importing deck {deck_id}: {str(e)}")
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        print(f"Error importing deck {deck_id}: {str(e)}")
        return jsonify({"success": False, "error": f"Error importing deck: {str(e)}"}), 500

def import_child_decks(source_deck, new_parent_id, deck_mapping):
    """
    Recursively import all child decks of the source deck
    
    Args:
        source_deck: The source deck object
        new_parent_id: The ID of the new parent deck
        deck_mapping: Dictionary mapping source deck IDs to new deck IDs
    """
    # Process each child deck
    for child_deck in source_deck.child_decks:
        # Create a new deck for this child
        new_child = FlashcardDecks(
            name=child_deck.name,  # Keep original name for sub-decks
            description=child_deck.description,
            parent_deck_id=new_parent_id,  # Set correct parent
            user_id=current_user.id,
            is_public=False  # Always start as private
        )
        db.session.add(new_child)
        db.session.flush()  # Get ID without committing
        
        # Remember the mapping
        deck_mapping[child_deck.flashcard_deck_id] = new_child.flashcard_deck_id
        
        # Copy flashcards for this child deck
        import_flashcards(child_deck.flashcard_deck_id, new_child.flashcard_deck_id)
        
        # Process this child's sub-decks recursively
        import_child_decks(child_deck, new_child.flashcard_deck_id, deck_mapping)

def import_flashcards(source_deck_id, target_deck_id):
    """
    Import all flashcards from source deck to target deck
    
    Args:
        source_deck_id: The ID of the source deck
        target_deck_id: The ID of the target deck
    
    Returns:
        The number of cards imported
    """
    # Get all flashcards from the source deck
    flashcards = Flashcards.query.filter_by(flashcard_deck_id=source_deck_id).all()
    
    imported_count = 0
    for card in flashcards:
        try:
            # Create a new flashcard based on the original
            new_card = Flashcards(
                flashcard_deck_id=target_deck_id,
                question=card.question,
                correct_answer=card.correct_answer,
                incorrect_answers=card.incorrect_answers,
                state=0,  # Reset state to 'new'
                due_date=None  # Reset due date
            )
            db.session.add(new_card)
            imported_count += 1
        except Exception as e:
            print(f"Error copying card {card.flashcard_id}: {str(e)}")
    
    print(f"Imported {imported_count} flashcards from deck {source_deck_id} to deck {target_deck_id}")
    return imported_count

def count_imported_cards(deck_id):
    """
    Count total cards in a deck hierarchy
    
    Args:
        deck_id: The ID of the root deck
    
    Returns:
        The total number of cards in the deck and all its sub-decks
    """
    # Use recursive CTE to find all decks in the hierarchy
    cte = db.session.query(
        FlashcardDecks.flashcard_deck_id.label('id')
    ).filter(
        FlashcardDecks.flashcard_deck_id == deck_id
    ).cte(name='count_decks', recursive=True)

    cte = cte.union_all(
        db.session.query(
            FlashcardDecks.flashcard_deck_id.label('id')
        ).filter(
            FlashcardDecks.parent_deck_id == cte.c.id
        )
    )
    
    # Count cards from all decks in the hierarchy
    count = Flashcards.query.filter(
        Flashcards.flashcard_deck_id.in_(db.session.query(cte.c.id))
    ).count()
    
    return count

@deck_api_bp.route('/update-overdue/<int:deck_id>', methods=['POST'])
@login_required
def update_overdue_cards(deck_id):
    """Update overdue cards to forgotten state"""
    try:
        # Check if deck belongs to the current user
        deck = FlashcardDecks.query.filter_by(
            flashcard_deck_id=deck_id, 
            user_id=current_user.id
        ).first_or_404()
        
        # Get update type from request body
        data = request.get_json(silent=True) or {}
        update_type = data.get('update_type', 'forgotten')
        
        if update_type != 'forgotten':
            return jsonify({'success': False, 'message': 'Invalid update type'}), 400
        
        # Execute raw SQL query to update overdue cards to forgotten state
        # This specific query handles both NULL and JSON fsrs_state
        result = db.session.execute("""
            UPDATE flashcards
            SET 
                state = 3,
                fsrs_state = 
                    CASE 
                        WHEN fsrs_state IS NULL THEN '{"state": 3, "step": 0}'::jsonb
                        ELSE jsonb_set(
                            jsonb_set(
                                fsrs_state::jsonb, 
                                '{state}', 
                                '3'::jsonb
                            ),
                            '{step}',
                            '0'::jsonb
                        )
                    END
            WHERE 
                due_date < NOW() 
                AND flashcard_deck_id = :deck_id
                AND state != 0  -- Skip new cards
                AND state != 3  -- Skip already forgotten cards
            RETURNING flashcard_id
        """, {'deck_id': deck_id})
        
        # Get the IDs of updated cards
        updated_ids = [row[0] for row in result]
        updated_count = len(updated_ids)
        
        # Commit changes
        db.session.commit()
        
        current_app.logger.info(f"Updated {updated_count} overdue cards to forgotten state for deck {deck_id}")
        
        return jsonify({
            'success': True, 
            'message': f'Updated {updated_count} overdue cards to forgotten state',
            'updated_count': updated_count,
            'updated_ids': updated_ids
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error updating overdue cards: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f"Database error: {str(e)}"
        }), 500
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating overdue cards: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f"Error: {str(e)}"
        }), 500
