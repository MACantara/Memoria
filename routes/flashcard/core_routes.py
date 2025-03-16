from flask import Blueprint, request, jsonify, render_template
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import process_review, get_current_time
from flask_login import current_user, login_required
import traceback

# Update blueprint name to be more specific since it's now part of flashcard package
flashcard_bp = Blueprint('flashcard', __name__)

@flashcard_bp.route("/deck/<int:deck_id>/view")
def view_flashcards(deck_id):
    """View all flashcards in a deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    flashcards = Flashcards.query.filter_by(flashcard_deck_id=deck_id)\
        .order_by(Flashcards.created_at.desc()).all()
    
    return render_template("view_flashcards.html", deck=deck, flashcards=flashcards)

@flashcard_bp.route("/update_progress", methods=["POST"])
def update_progress():
    """Update flashcard study progress"""
    try:
        data = request.json
        flashcard_id = data['flashcard_id']
        is_correct = data['is_correct']
        
        # Get the flashcard
        flashcard = Flashcards.query.get_or_404(flashcard_id)
        print(f"Processing flashcard {flashcard_id}, is_correct: {is_correct}")
        
        # Use timezone-aware datetime
        from services.fsrs_scheduler import get_current_time
        flashcard.last_reviewed = get_current_time()
        
        # Try to update FSRS stats if possible
        try:
            # If flashcard has no FSRS state yet, initialize it
            if not flashcard.fsrs_state:
                try:
                    flashcard.init_fsrs_state()
                    print("FSRS state initialized")
                except Exception as e:
                    print(f"Error initializing FSRS state: {e}")
            
            # Process the review with FSRS
            next_due, retrievability = process_review(flashcard, is_correct)
            print(f"FSRS updated: next_due={next_due.isoformat()}, retrievability={retrievability}")
        except Exception as e:
            print(f"Error in FSRS processing: {e}")
            print(traceback.format_exc())
            # Save the base update
            db.session.add(flashcard)
            db.session.commit()
        
        # Format dates using isoformat for consistent output
        last_reviewed_str = flashcard.last_reviewed.isoformat() if flashcard.last_reviewed else None
        next_due_str = flashcard.due_date.isoformat() if flashcard.due_date else None
        
        # Return progress update with whatever data we have
        return jsonify({
            "success": True,
            "last_reviewed": last_reviewed_str,
            "is_correct": is_correct,
            "next_due": next_due_str,
            "retrievability": getattr(flashcard, 'retrievability', 0.0),
            "state": flashcard.get_state_name() if hasattr(flashcard, 'get_state_name') else "unknown"
        })
            
    except Exception as e:
        print(f"Error in update_progress: {e}")
        print(traceback.format_exc())  # Print full stack trace
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@flashcard_bp.route("/create", methods=["POST"])
@login_required
def create_flashcard():
    """Create a new flashcard manually"""
    try:
        data = request.json
        deck_id = data.get('deck_id')
        question = data.get('question')
        correct_answer = data.get('correct_answer')
        incorrect_answers = data.get('incorrect_answers', [])
        
        # Validate required fields
        if not all([deck_id, question, correct_answer]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400
            
        # Verify deck ownership
        deck = FlashcardDecks.query.get_or_404(deck_id)
        if deck.user_id != current_user.id:
            return jsonify({"success": False, "error": "You don't have permission to add cards to this deck"}), 403
        
        # Create the flashcard
        current_time = get_current_time()
        
        flashcard = Flashcards(
            question=question,
            correct_answer=correct_answer,
            incorrect_answers=incorrect_answers[:3],  # Limit to 3 incorrect answers
            flashcard_deck_id=deck_id,
            due_date=current_time,
            state=0  # New card
        )
        
        # Initialize FSRS state for the card
        flashcard.init_fsrs_state()
        
        db.session.add(flashcard)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Flashcard created successfully",
            "flashcard_id": flashcard.flashcard_id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating flashcard: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@flashcard_bp.route("/update/<int:flashcard_id>", methods=["PUT"])
@login_required
def update_flashcard(flashcard_id):
    """Update an existing flashcard"""
    try:
        data = request.json
        question = data.get('question')
        correct_answer = data.get('correct_answer')
        incorrect_answers = data.get('incorrect_answers', [])
        
        # Validate required fields
        if not all([question, correct_answer]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400
            
        # Get the flashcard
        flashcard = Flashcards.query.get_or_404(flashcard_id)
        
        # Verify ownership through deck
        deck = FlashcardDecks.query.get(flashcard.flashcard_deck_id)
        if not deck or deck.user_id != current_user.id:
            return jsonify({"success": False, "error": "You don't have permission to edit this flashcard"}), 403
        
        # Update the flashcard
        flashcard.question = question
        flashcard.correct_answer = correct_answer
        flashcard.incorrect_answers = incorrect_answers[:3]  # Limit to 3 incorrect answers
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Flashcard updated successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating flashcard: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@flashcard_bp.route("/delete/<int:flashcard_id>", methods=["DELETE"])
@login_required
def delete_flashcard(flashcard_id):
    """Delete a flashcard"""
    try:
        # Get the flashcard
        flashcard = Flashcards.query.get_or_404(flashcard_id)
        
        # Verify ownership through deck
        deck = FlashcardDecks.query.get(flashcard.flashcard_deck_id)
        if not deck or deck.user_id != current_user.id:
            return jsonify({"success": False, "error": "You don't have permission to delete this flashcard"}), 403
        
        # Delete the flashcard
        db.session.delete(flashcard)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Flashcard deleted successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting flashcard: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500
