from flask import Blueprint, request, jsonify, render_template
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
import traceback
from services.fsrs_scheduler import get_current_time

flashcard_bp = Blueprint('flashcard', __name__)

@flashcard_bp.route("/update_progress", methods=["POST"])
def update_progress():
    """Update a flashcard's progress after review"""
    try:
        data = request.json
        flashcard_id = data['flashcard_id']
        is_correct = data['is_correct']
        
        # Get the flashcard
        flashcard = Flashcards.query.get_or_404(flashcard_id)
        print(f"Processing flashcard {flashcard_id}, is_correct: {is_correct}")
        
        # First update the basic stats to ensure we have some progress
        if is_correct:
            flashcard.correct_count += 1
        else:
            flashcard.incorrect_count += 1
        
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
            
            # Process the review with FSRS if possible
            try:
                from services.fsrs_scheduler import process_review
                next_due, retrievability = process_review(flashcard, is_correct)
                print(f"FSRS updated: next_due={next_due.isoformat()}, retrievability={retrievability}")
            except Exception as e:
                print(f"Error in FSRS processing: {e}")
                print(traceback.format_exc())
                # Continue with basic tracking
                db.session.add(flashcard)
                db.session.commit()
        except Exception as e:
            # Fallback to basic updates if FSRS fails completely
            print(f"Using fallback progress update: {e}")
            db.session.add(flashcard)
            db.session.commit()
        
        # Format dates using isoformat for consistent output
        last_reviewed_str = flashcard.last_reviewed.isoformat() if flashcard.last_reviewed else None
        next_due_str = flashcard.due_date.isoformat() if flashcard.due_date else None
        
        # Return progress update with whatever data we have
        return jsonify({
            "success": True,
            "correct_count": flashcard.correct_count,
            "incorrect_count": flashcard.incorrect_count,
            "last_reviewed": last_reviewed_str,
            "is_correct": is_correct,
            "next_due": next_due_str,
            "retrievability": getattr(flashcard, 'retrievability', 0.0),
            "state": flashcard.get_state_name() if hasattr(flashcard, 'get_state_name') else "unknown"
        })
            
    except Exception as e:
        print(f"Error in update_progress: {e}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@flashcard_bp.route("/deck/<int:deck_id>/view")
def view_flashcards(deck_id):
    """View all flashcards in a deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    flashcards = Flashcards.query.filter_by(flashcard_deck_id=deck_id)\
        .order_by(Flashcards.created_at.desc()).all()
    
    return render_template("view_flashcards.html", deck=deck, flashcards=flashcards)

# Import and register other flashcard-related blueprints
from routes.flashcard_generation_routes import generation_bp
from routes.flashcard_stats_routes import stats_bp

# Register blueprints with correct URL prefixes
flashcard_bp.register_blueprint(generation_bp, url_prefix='/generation')
flashcard_bp.register_blueprint(stats_bp, url_prefix='/stats')
