from flask import Blueprint, request, jsonify, redirect, url_for, Response, stream_with_context
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
from google import genai
import json
import os
import re
import time

generation_bp = Blueprint('generation', __name__)

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

@generation_bp.route("/generate-flashcards", methods=["POST", "GET"])
def generate():
    """Generate flashcards using AI"""
    # For GET requests (EventSource/SSE streaming)
    if request.method == "GET":
        topic = request.args.get("topic")
        parent_deck_id = request.args.get("parent_deck_id")
        batch_size = 100
        
        if not topic:
            return jsonify({"error": "Topic is required"}), 400
            
        return stream_flashcard_generation(topic, parent_deck_id, batch_size)
    
    # For POST requests (traditional form submission)
    else:
        topic = request.form.get("topic")
        parent_deck_id = request.form.get("parent_deck_id")
        batch_size = int(request.form.get("batch_size", 100))
        
        # Check if client supports EventSource
        accept_header = request.headers.get("Accept", "")
        if "text/event-stream" in accept_header:
            # Client explicitly requested server-sent events
            return stream_flashcard_generation(topic, parent_deck_id, batch_size)
        else:
            # Traditional synchronous response
            return generate_flashcards_sync(topic, parent_deck_id, batch_size)

def generate_flashcards_sync(topic, parent_deck_id, batch_size):
    """Traditional synchronous flashcard generation"""
    # Create deck
    deck = create_deck(topic, parent_deck_id)
    
    client = genai.Client(api_key=api_key)
    prompt_template = create_generation_prompt(topic, batch_size)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt_template
        )
        
        batch_cards = parse_flashcards(response.text)
        if not batch_cards:
            raise ValueError("No valid flashcards generated")
            
        save_flashcards_to_db(batch_cards, deck.flashcard_deck_id)
            
    except Exception as e:
        print(f"Error in flashcard generation: {e}")
        db.session.rollback()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            "success": True, 
            "redirect_url": url_for('deck.get_deck_flashcards', deck_id=deck.flashcard_deck_id)
        })
    return redirect(url_for('deck.get_deck_flashcards', deck_id=deck.flashcard_deck_id))

def stream_flashcard_generation(topic, parent_deck_id, batch_size):
    """Stream flashcard generation using Server-Sent Events"""
    @stream_with_context
    def generate_stream():
        # Create the deck first
        try:
            deck = create_deck(topic, parent_deck_id)
            yield f"data: {json.dumps({'type': 'deck_created', 'deck_id': deck.flashcard_deck_id, 'name': deck.name})}\n\n"
            
            client = genai.Client(api_key=api_key)
            prompt_template = create_generation_prompt(topic, batch_size)
            
            # Start streaming response
            stream = client.models.generate_content_stream(
                model="gemini-2.0-flash-lite",
                contents=prompt_template
            )
            
            # For parsing incomplete chunks
            buffer = ""
            flashcards_generated = 0
            
            for chunk in stream:
                if not chunk.text:
                    continue
                    
                # Add chunk to buffer for parsing
                buffer += chunk.text
                
                # Try to extract complete flashcards from buffer
                cards, remaining = extract_complete_flashcards(buffer)
                buffer = remaining  # Keep remaining text for next iteration
                
                if cards:
                    # Save cards to database
                    new_cards_count = save_flashcards_to_db(cards, deck.flashcard_deck_id)
                    flashcards_generated += new_cards_count
                    
                    # Send progress update
                    progress = min(100, int((flashcards_generated / batch_size) * 100))
                    yield f"data: {json.dumps({'type': 'progress', 'count': flashcards_generated, 'total': batch_size, 'percentage': progress})}\n\n"
                    
                    # Send sample cards for display
                    for card in cards[:min(2, len(cards))]:  # Send max 2 cards per update
                        yield f"data: {json.dumps({'type': 'card', 'question': card['question'][:50] + '...', 'correct': card['correct_answer'][:30] + '...'})}\n\n"
            
            # Process any remaining text in buffer
            if buffer:
                cards, _ = extract_complete_flashcards(buffer, force_parse=True)
                if cards:
                    new_cards_count = save_flashcards_to_db(cards, deck.flashcard_deck_id)
                    flashcards_generated += new_cards_count
            
            # Send completion message
            yield f"data: {json.dumps({'type': 'complete', 'count': flashcards_generated, 'redirect_url': url_for('deck.get_deck_flashcards', deck_id=deck.flashcard_deck_id)})}\n\n"
            
        except Exception as e:
            error_message = str(e)
            print(f"Error in streaming flashcard generation: {error_message}")
            yield f"data: {json.dumps({'type': 'error', 'message': error_message})}\n\n"
            db.session.rollback()
    
    return Response(generate_stream(), mimetype="text/event-stream")

def create_deck(topic, parent_deck_id):
    """Create a new flashcard deck"""
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
    return deck

def save_flashcards_to_db(cards, deck_id):
    """Save parsed flashcards to the database"""
    cards_added = 0
    for card in cards:
        # Check if card with same question already exists in this deck
        if not Flashcards.query.filter_by(
            flashcard_deck_id=deck_id,
            question=card['question']
        ).first():
            flashcard = Flashcards(
                question=card['question'],
                correct_answer=card['correct_answer'],
                incorrect_answers=json.dumps(card['incorrect_answers']),
                flashcard_deck_id=deck_id
            )
            db.session.add(flashcard)
            cards_added += 1
    
    db.session.commit()
    return cards_added

def extract_complete_flashcards(text, force_parse=False):
    """Extract complete flashcards from a text chunk, returning parsed cards and remaining text"""
    cards = []
    remaining = text
    
    # Use regex pattern to find complete flashcard entries
    pattern = r'question:\s*(.*?)\s*correct:\s*(.*?)\s*incorrect:\s*(.*?)(?=\s*question:|$)'
    
    matches = re.finditer(pattern, text, re.DOTALL)
    last_end = 0
    
    for match in matches:
        try:
            question = match.group(1).strip()
            correct_answer = match.group(2).strip()
            incorrect_answers_text = match.group(3).strip()
            
            incorrect_answers = [
                ans.strip().split('**')[0].strip() # Remove any **text** markers
                for ans in incorrect_answers_text.split(";")
                if ans.strip()
            ]
            
            # Clean up any remaining markdown or extra text
            question = question.replace('*', '').strip()
            correct_answer = correct_answer.replace('*', '').strip()
            
            if len(incorrect_answers) >= 3:
                cards.append({
                    "question": question,
                    "correct_answer": correct_answer,
                    "incorrect_answers": incorrect_answers[:3],
                })
                
            last_end = match.end()
        except Exception as e:
            print(f"Error parsing flashcard from chunk: {e}")
            continue
    
    # Keep the remaining text that doesn't contain complete flashcards
    if last_end > 0:
        remaining = text[last_end:]
    
    # If forcing parsing (end of stream), try to extract any partial cards
    if force_parse and not cards and "question:" in remaining:
        try:
            parts = remaining.split("question:")
            for part in parts[1:]:  # Skip first empty part
                try:
                    if "correct:" not in part:
                        continue
                        
                    correct_idx = part.index("correct:")
                    question = part[:correct_idx].strip()
                    
                    correct_part = part[correct_idx + len("correct:"):]
                    
                    if "incorrect:" not in correct_part:
                        continue
                        
                    incorrect_idx = correct_part.index("incorrect:")
                    correct_answer = correct_part[:incorrect_idx].strip()
                    
                    incorrect_part = correct_part[incorrect_idx + len("incorrect:"):]
                    incorrect_answers = [
                        ans.strip() for ans in incorrect_part.split(";")
                        if ans.strip()
                    ]
                    
                    if len(incorrect_answers) >= 3:
                        cards.append({
                            "question": question,
                            "correct_answer": correct_answer,
                            "incorrect_answers": incorrect_answers[:3]
                        })
                except Exception as e:
                    print(f"Error in force parsing: {e}")
                    continue
        except Exception as e:
            print(f"Error in final parsing: {e}")
            
        # No more remaining text if we've parsed everything
        remaining = ""
    
    return cards, remaining

def create_generation_prompt(topic, batch_size):
    """Create a prompt template for flashcard generation"""
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

def parse_flashcards(text):
    """Parse generated text into structured flashcard data"""
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
