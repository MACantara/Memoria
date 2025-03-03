from flask import Blueprint, request, jsonify, redirect, url_for
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
from google import genai
import json
import os
from services.fsrs_scheduler import get_current_time

generation_bp = Blueprint('generation', __name__)

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

@generation_bp.route("/generate-flashcards", methods=["POST"])
def generate():
    """Generate flashcards using AI"""
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
    prompt_template = generate_prompt_template(deck.name, batch_size)
    print(f"Generating flashcards for topic: '{deck.name}', batch size: {batch_size}")

    try:
        # Use schema with shorter field names for optimization
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},  # short for question
                    "ca": {"type": "string"}, # short for correct_answer
                    "ia": {                   # short for incorrect_answers
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 3
                    }
                },
                "required": ["q", "ca", "ia"]
            }
        }
        
        print("Sending request to Gemini API...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt_template,
            config={
                'response_mime_type': 'application/json',
                'response_schema': schema
            }
        )
        
        print("\n==== RAW GEMINI API RESPONSE ====")
        print(response.text[:1000] + "..." if len(response.text) > 1000 else response.text)
        print("===== END OF RAW RESPONSE =====\n")
        
        # Parse JSON response
        try:
            # Try to parse the response as JSON
            flashcards_data = json.loads(response.text)
            print(f"Successfully parsed JSON output: {len(flashcards_data)} cards")
            
            # Print sample cards for debugging with the new field names
            if flashcards_data:
                print("\n==== SAMPLE FLASHCARD DATA ====")
                sample_count = min(2, len(flashcards_data))
                for i in range(sample_count):
                    print(f"Card {i+1}:")
                    print(f"  Question: {flashcards_data[i].get('q')}")
                    print(f"  Correct: {flashcards_data[i].get('ca')}")
                    print(f"  Incorrect: {flashcards_data[i].get('ia')}")
                print("============================\n")
            
        except json.JSONDecodeError as parse_error:
            # Fallback to manual parsing if JSON parsing fails
            print(f"JSON parsing failed: {parse_error}. Falling back to manual parsing.")
            flashcards_data = parse_flashcards(response.text)
            print(f"Manual parsing result: {len(flashcards_data)} cards extracted")
            
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
                
            if not Flashcards.query.filter_by(
                flashcard_deck_id=deck.flashcard_deck_id,
                question=question
            ).first():
                # Pad with empty answers if needed - FIXED LINE BELOW
                while len(incorrect_answers) < 3:
                    incorrect_answers.append(f"Incorrect answer {len(incorrect_answers) + 1}")
                
                flashcard = Flashcards(
                    question=question,
                    correct_answer=correct_answer,
                    incorrect_answers=json.dumps(incorrect_answers),
                    flashcard_deck_id=deck.flashcard_deck_id,
                    due_date=current_time,
                    state=0
                )
                db.session.add(flashcard)
                cards_added += 1
        
        db.session.commit()
            
    except Exception as e:
        print(f"Error in flashcard generation: {e}")
        import traceback
        print(traceback.format_exc())  # Print full stack trace for debugging
        db.session.rollback()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "redirect_url": url_for('deck.deck_view.get_deck_flashcards', deck_id=deck.flashcard_deck_id)})
    return redirect(url_for('deck.deck_view.get_deck_flashcards', deck_id=deck.flashcard_deck_id))


def generate_prompt_template(topic, batch_size):
    """Generate a prompt template for AI flashcard generation"""
    return f"""You are an expert educator creating flashcards about {topic}.
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
    
    Format your response as a JSON array of objects, each with:
    - 'q': the flashcard question (short for question)
    - 'ca': the correct answer (short for correct_answer)
    - 'ia': array of exactly three incorrect answers (short for incorrect_answers)

    Generate {batch_size} unique flashcards covering different aspects of the topic.
    Ensure comprehensive coverage by:
    1. Breaking down the topic into key subtopics
    2. Creating equal numbers of cards for each subtopic
    3. Varying question types within each subtopic
    4. Including both fundamental and advanced concepts
    5. Maintaining consistent answer length and style throughout"""


def parse_flashcards(text):
    """Fallback parser for when structured output fails"""
    try:
        # First try to parse as JSON
        data = json.loads(text)
        
        # Process the data to normalize field names
        if isinstance(data, list):
            # Convert short names to standard names if needed
            normalized_data = []
            for card in data:
                normalized = {}
                # Handle both short and long field names
                normalized['question'] = card.get('q', card.get('question', ''))
                normalized['correct_answer'] = card.get('ca', card.get('correct_answer', ''))
                normalized['incorrect_answers'] = card.get('ia', card.get('incorrect_answers', []))
                normalized_data.append(normalized)
            return normalized_data
        elif isinstance(data, dict) and "flashcards" in data:
            return data["flashcards"]
    except:
        # If JSON parsing fails, use the traditional text parsing
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
                        "question": question,
                        "correct_answer": correct_answer,
                        "incorrect_answers": incorrect_answers[:3],
                    })
            except ValueError as e:
                print(f"Error parsing flashcard: {e}")
                continue

        return flashcards
