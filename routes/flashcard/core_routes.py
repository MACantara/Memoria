from flask import Blueprint, request, jsonify, render_template
from models import db, FlashcardDecks, Flashcards
from services.fsrs_scheduler import process_review
import traceback

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
