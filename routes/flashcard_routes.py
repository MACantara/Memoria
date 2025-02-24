from flask import Blueprint, request, jsonify, redirect, url_for
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
from google import genai
import json
import os

flashcard_bp = Blueprint('flashcard', __name__)

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

@flashcard_bp.route("/generate-flashcards", methods=["POST"])
def generate():
    deck_name = request.form["topic"]
    batch_size = 100
    
    deck = FlashcardDecks(
        name=deck_name,
        description=f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        parent_deck_id=None
    )
    db.session.add(deck)
    db.session.commit()

    client = genai.Client(api_key=api_key)
    # Move prompt template to a separate config or template file
    prompt_template = f"""You are an expert educator creating flashcards about {deck_name}.
    Generate comprehensive, accurate, and engaging flashcards following these guidelines:

    1. Each flashcard must have:
       - A clear, concise question that tests understanding
       - One definitively correct answer
       - Three plausible but incorrect answers
       - All answers should be roughly the same length and style
    
    2. Question types should include:
       - Factual recall (25% of cards)
       - Concept application (25% of cards)
       - Problem-solving (25% of cards)
       - Relationships between concepts (25% of cards)
    
    3. Ensure:
       - No duplicate questions or answers
       - All content is factually accurate
       - Clear, unambiguous wording
       - Progressive difficulty (easy -> medium -> hard)
    
    4. Format each flashcard exactly as:
    question: [question text]
    correct: [correct answer]
    incorrect: [wrong answer 1]; [wrong answer 2]; [wrong answer 3]

    Generate exactly {batch_size} unique flashcards covering different aspects of the topic.
    Ensure comprehensive coverage by:
    1. Breaking down the topic into key subtopics
    2. Creating equal numbers of cards for each subtopic
    3. Varying question types within each subtopic
    4. Including both fundamental and advanced concepts"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite-preview-02-05",
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
    data = request.json
    flashcard = Flashcards.query.get_or_404(data['flashcard_id'])
    
    if data['is_correct']:
        flashcard.correct_count += 1
    else:
        flashcard.incorrect_count += 1
    
    flashcard.last_reviewed = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True})

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
