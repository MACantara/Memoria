from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from models import db, FlashcardDecks, Flashcards
from datetime import datetime, timezone
from google import genai
import json
import os
from services.fsrs_scheduler import process_review, get_stats
import traceback

flashcard_bp = Blueprint('flashcard', __name__)

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

@flashcard_bp.route("/generate-flashcards", methods=["POST"])
def generate():
    topic = request.form["topic"]
    parent_deck_id = request.form.get("parent_deck_id")
    batch_size = 100
    
    if parent_deck_id:
        parent_deck = FlashcardDecks.query.get_or_404(parent_deck_id)
        deck = FlashcardDecks(
            name=topic if topic else f"Generated cards for {parent_deck.name}",
            description=f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            parent_deck_id=parent_deck_id
        )
    else:
        deck = FlashcardDecks(
            name=topic,
            description=f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            parent_deck_id=None
        )
    
    db.session.add(deck)
    db.session.commit()

    client = genai.Client(api_key=api_key)
    # Move prompt template to a separate config or template file
    prompt_template = f"""You are an expert educator creating flashcards about {deck.name}.
    Generate comprehensive, accurate, and engaging flashcards following these strict guidelines:

    1. Each flashcard must have:
       - A clear, concise question that tests understanding
       - One definitively correct answer
       - Three plausible but incorrect answers
       - CRITICAL: All answers (correct and incorrect) MUST:
         * Be similar in length (within 10-15 characters of each other)
         * Use the same level of detail and complexity
         * Follow the same grammatical structure
         * Be equally specific/general
    
    2. Question types must be evenly distributed:
       - Factual recall (25% of cards)
       - Concept application (25% of cards)
       - Problem-solving (25% of cards)
       - Relationships between concepts (25% of cards)
    
    3. Ensure quality control:
       - No duplicate questions or answers
       - All content is factually accurate
       - Clear, unambiguous wording
       - Progressive difficulty (easy -> medium -> hard)
       - Avoid answers that are obviously wrong
       - Don't make the correct answer stand out by length or detail
    
    4. Format each flashcard exactly as:
    question: [question text]
    correct: [correct answer]
    incorrect: [wrong answer 1]; [wrong answer 2]; [wrong answer 3]

    Generate exactly {batch_size} unique flashcards covering different aspects of the topic.
    Ensure comprehensive coverage by:
    1. Breaking down the topic into key subtopics
    2. Creating equal numbers of cards for each subtopic
    3. Varying question types within each subtopic
    4. Including both fundamental and advanced concepts
    5. Maintaining consistent answer length and style throughout"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt_template
        )
        
        batch_cards = parse_flashcards(response.text)
        if not batch_cards:
            raise ValueError("No valid flashcards generated")
            
        cards_added = 0
        for card in batch_cards:
            if not Flashcards.query.filter_by(
                flashcard_deck_id=deck.flashcard_deck_id,
                question=card['question']
            ).first():
                flashcard = Flashcards(
                    question=card['question'],
                    correct_answer=card['correct_answer'],
                    incorrect_answers=json.dumps(card['incorrect_answers']),
                    flashcard_deck_id=deck.flashcard_deck_id
                )
                db.session.add(flashcard)
                cards_added += 1
        
        db.session.commit()
            
    except Exception as e:
        print(f"Error in flashcard generation: {e}")
        db.session.rollback()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "redirect_url": url_for('deck.get_deck_flashcards', deck_id=deck.flashcard_deck_id)})
    return redirect(url_for('deck.get_deck_flashcards', deck_id=deck.flashcard_deck_id))

@flashcard_bp.route("/update_progress", methods=["POST"])
def update_progress():
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
                    # Continue with basic tracking
            
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
        print(traceback.format_exc())  # Print full stack trace
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@flashcard_bp.route("/deck/<int:deck_id>/view")
def view_flashcards(deck_id):
    """View all flashcards in a deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    flashcards = Flashcards.query.filter_by(flashcard_deck_id=deck_id)\
        .order_by(Flashcards.created_at.desc()).all()
    
    return render_template("view_flashcards.html", deck=deck, flashcards=flashcards)

@flashcard_bp.route("/deck/<int:deck_id>/view_stats")
def view_deck_stats(deck_id):
    """View spaced repetition stats for a deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    return render_template("stats.html", deck=deck)

@flashcard_bp.route("/deck/<int:deck_id>/stats")
def deck_stats(deck_id):
    """Get spaced repetition stats for a deck"""
    deck = FlashcardDecks.query.get_or_404(deck_id)
    stats = get_stats(deck_id)
    return jsonify(stats)

def parse_flashcards(text):
    flashcards = []
    flashcard_responses = text.split("question:")

    for card_response in flashcard_responses[1:]:  # Skip first empty split
        try:
            question_start = 0
            correct_start = card_response.lower().index("correct:") + len("correct:")
            incorrect_start = card_response.lower().index("incorrect:") + len("incorrect:")
            
            question = card_response[question_start:correct_start].replace("correct:", "").strip()
            correct_answer = card_response[correct_start:incorrect_start].replace("incorrect:", "").strip()
            incorrect_answers = [
                ans.strip().split('**')[0].strip() # Remove any **text** markers
                for ans in card_response[incorrect_start:].split(";")
                if ans.strip()
            ]

            # Clean up any remaining markdown or extra text
            question = question.replace('*', '').strip()
            correct_answer = correct_answer.replace('*', '').strip()
            
            if len(incorrect_answers) >= 3:  # Ensure we have enough wrong answers
                flashcards.append({
                    "question": question,
                    "correct_answer": correct_answer,
                    "incorrect_answers": incorrect_answers[:3],  # Take only first 3 wrong answers
                })
        except ValueError as e:
            print(f"Error parsing flashcard: {e}")
            continue

    return flashcards
