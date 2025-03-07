from flask import Blueprint, request, jsonify, redirect, url_for, current_app
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
from google import genai
import json
import re
import os
import traceback
from services.fsrs_scheduler import get_current_time
from config import Config

generation_bp = Blueprint('generation', __name__)

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

@generation_bp.route("/generate-flashcards", methods=["POST"])
def generate():
    """Generate flashcards using AI"""
    topic = request.form["topic"]
    parent_deck_id = request.form.get("parent_deck_id")
    batch_size = Config.DEFAULT_BATCH_SIZE
    
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
    prompt_template = Config.generate_prompt_template(deck.name, batch_size)
    current_app.logger.info(f"Generating flashcards for topic: '{deck.name}', batch size: {batch_size}")

    try:
        current_app.logger.info("Sending request to Gemini API...")
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt_template,
            config=Config.GEMINI_CONFIG
        )
        
        current_app.logger.debug(f"RAW GEMINI API RESPONSE: {response.text}")
        
        # Parse JSON response with improved error handling
        flashcards_data = []
        try:
            # Try to repair and parse the JSON
            repaired_json = repair_json(response.text)
            flashcards_data = json.loads(repaired_json)
            current_app.logger.info(f"Successfully parsed JSON output: {len(flashcards_data)} cards")
            
        except json.JSONDecodeError as parse_error:
            current_app.logger.error(f"JSON parsing failed: {parse_error}.")
            
            # Try regex extraction as a fallback
            current_app.logger.info("Attempting to extract cards using regex pattern matching")
            flashcards_data = extract_cards_from_text(response.text)
            
            if flashcards_data:
                current_app.logger.info(f"Successfully extracted {len(flashcards_data)} cards using pattern matching")
            else:
                # Last resort - use traditional text parsing
                current_app.logger.info("Falling back to traditional parsing")
                flashcards_data = parse_flashcards_traditional(response.text)
                current_app.logger.info(f"Traditional parsing result: {len(flashcards_data)} cards extracted")
            
        if not flashcards_data:
            raise ValueError("No valid flashcards generated")
            
        cards_added = 0
        # Set current time for all cards to use same timestamp
        current_time = get_current_time()
        
        for card in flashcards_data:
            # Convert to dict if it's a Pydantic model
            if hasattr(card, 'model_dump'):
                card = card.model_dump()
                
            # Use the abbreviated field names (with fallback to old names)
            question = card.get('q', card.get('question', ''))
            correct_answer = card.get('ca', card.get('correct_answer', ''))
            incorrect_answers = card.get('ia', card.get('incorrect_answers', []))[:3]
                
            if not question or not correct_answer:
                current_app.logger.warning(f"Skipping incomplete card: {card}")
                continue
                
            if not Flashcards.query.filter_by(
                flashcard_deck_id=deck.flashcard_deck_id,
                question=question
            ).first():
                # Pad with empty answers if needed
                while len(incorrect_answers) < 3:
                    incorrect_answers.append(f"Incorrect answer {len(incorrect_answers) + 1}")
                
                flashcard = Flashcards(
                    question=question,
                    correct_answer=correct_answer,
                    incorrect_answers=incorrect_answers,
                    flashcard_deck_id=deck.flashcard_deck_id,
                    due_date=current_time,
                    state=0
                )
                
                # Initialize FSRS state
                flashcard.init_fsrs_state()
                
                db.session.add(flashcard)
                cards_added += 1
        
        db.session.commit()
        current_app.logger.info(f"Successfully added {cards_added} flashcards to deck {deck.flashcard_deck_id}")
            
    except Exception as e:
        current_app.logger.error(f"Error in flashcard generation: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        db.session.rollback()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "redirect_url": url_for('deck.deck_view.get_deck_flashcards', deck_id=deck.flashcard_deck_id)})
    return redirect(url_for('deck.deck_view.get_deck_flashcards', deck_id=deck.flashcard_deck_id))

def repair_json(json_str):
    """Attempt to repair malformed JSON strings"""
    # Remove any whitespace and newlines at the beginning
    json_str = json_str.strip()
    
    # Make sure it starts with a valid JSON character
    if not json_str.startswith('[') and not json_str.startswith('{'):
        # Try to find the first valid JSON starting point
        start_idx = json_str.find('[')
        if start_idx == -1:
            start_idx = json_str.find('{')
        
        if start_idx != -1:
            json_str = json_str[start_idx:]
    
    # Make sure brackets are balanced (simple approach)
    bracket_stack = []
    for i, char in enumerate(json_str):
        if char in '{[':
            bracket_stack.append(char)
        elif char == '}' and bracket_stack and bracket_stack[-1] == '{':
            bracket_stack.pop()
        elif char == ']' and bracket_stack and bracket_stack[-1] == '[':
            bracket_stack.pop()
    
    # Close any unclosed brackets
    if bracket_stack:
        for bracket in reversed(bracket_stack):
            closing = '}' if bracket == '{' else ']'
            json_str += closing
    
    return json_str

def extract_cards_from_text(text):
    """Extract flashcards from text using regex patterns"""
    cards = []
    
    # Look for card patterns like {"q": "question", "ca": "answer", "ia": ["wrong1", "wrong2", "wrong3"]}
    card_pattern = r'{\s*"q":\s*"([^"]+)",\s*"ca":\s*"([^"]+)",\s*"ia":\s*\[(.*?)\]\s*}'
    matches = re.finditer(card_pattern, text, re.DOTALL)
    
    for match in matches:
        question = match.group(1)
        correct_answer = match.group(2)
        incorrect_answers_raw = match.group(3)
        
        # Extract the incorrect answers
        ia_pattern = r'"([^"]+)"'
        incorrect_answers = re.findall(ia_pattern, incorrect_answers_raw)
        
        # Create a card and add it to the list
        if question and correct_answer and incorrect_answers:
            card = {
                'q': question,
                'ca': correct_answer,
                'ia': incorrect_answers[:3]  # Limit to 3 incorrect answers
            }
            cards.append(card)
    
    return cards

def parse_flashcards_traditional(text):
    """Traditional fallback parser for when all else fails"""
    flashcards = []
    flashcard_responses = text.split("question:")

    for card_response in flashcard_responses[1:]:  # Skip first empty split
        try:
            question_start = 0
            correct_start = card_response.lower().index("correct:") + len("correct:")
            incorrect_start = card_response.lower().index("incorrect:") + len("incorrect:")
            
            question = card_response[question_start:correct_start].replace("correct:", "").strip()
            correct_answer = card_response[correct_start:incorrect_start].replace("incorrect:", "").strip()
            
            # Clean up and parse incorrect answers
            incorrect_answers = []
            for ans in card_response[incorrect_start:].split(";"):
                if ans.strip():
                    incorrect_answers.append(ans.strip())
            
            if len(incorrect_answers) >= 3:  # Ensure we have enough wrong answers
                flashcards.append({
                    "q": question,
                    "ca": correct_answer,
                    "ia": incorrect_answers[:3],
                })
        except ValueError as e:
            current_app.logger.error(f"Error parsing flashcard: {e}")
            continue

    return flashcards
