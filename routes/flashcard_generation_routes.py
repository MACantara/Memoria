from flask import Blueprint, request, jsonify, redirect, url_for, render_template, current_app
from models import db, FlashcardDecks, Flashcards
from datetime import datetime
from google import genai
import json
import os
import re
import time
import threading
import traceback
from services.generation_tracker import (
    create_job, update_job, get_job, add_sample_card,
    STATUS_PENDING, STATUS_GENERATING, STATUS_COMPLETED, STATUS_FAILED
)

# Create blueprint with correct name and no url_prefix (handled by parent)
generation_bp = Blueprint('generation', __name__)

@generation_bp.route("/generate-flashcards", methods=["POST"])
def generate():
    """Start flashcard generation process and return a job ID for tracking"""
    topic = request.form.get("topic")
    parent_deck_id = request.form.get("parent_deck_id")
    batch_size = int(request.form.get("batch_size", 100))
    
    if not topic:
        return jsonify({"error": "Topic is required"}), 400
        
    # Create the deck first
    try:
        deck = create_deck(topic, parent_deck_id)
        
        # Create a job for tracking
        job_id = create_job(deck_id=deck.flashcard_deck_id, topic=topic)
        update_job(
            job_id,
            status=STATUS_GENERATING,
            message=f"Starting generation for {topic}...",
            total_cards=batch_size,
            redirect_url=url_for('deck.get_deck_flashcards', deck_id=deck.flashcard_deck_id)
        )
        
        # Capture the current app for the background thread
        app = current_app._get_current_object()
        
        # Start background thread for card generation
        thread = threading.Thread(
            target=generate_cards_in_background,
            args=(app, job_id, topic, deck.flashcard_deck_id, batch_size)
        )
        thread.daemon = True
        thread.start()
        
        # Return immediately with job ID
        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": "Generation started",
            "deck_id": deck.flashcard_deck_id
        })
        
    except Exception as e:
        error_message = str(e)
        print(f"Error starting flashcard generation: {error_message}")
        return jsonify({"error": error_message}), 500

@generation_bp.route("/generation-progress/<job_id>", methods=["GET"])
def check_progress(job_id):
    """Check progress of a flashcard generation job"""
    job = get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
        
    return jsonify(job)

@generation_bp.route("/generation-status", methods=["GET"])
def generation_status_page():
    """Render page that shows generation progress"""
    job_id = request.args.get("job_id")
    deck_id = request.args.get("deck_id")
    
    if not job_id or not deck_id:
        return redirect(url_for('main.index'))
    
    deck = FlashcardDecks.query.get_or_404(deck_id)
    
    return render_template(
        "generation_progress.html", 
        job_id=job_id, 
        deck_id=deck_id,
        deck_name=deck.name
    )

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

def generate_cards_in_background(app, job_id, topic, deck_id, batch_size):
    """Background process to generate flashcards with proper application context using streaming"""
    # Create application context for this thread
    with app.app_context():
        try:
            update_job(
                job_id,
                message="Connecting to AI model...",
                progress=5
            )
            
            api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
            if not api_key:
                raise ValueError("API key for Gemini not configured")
                
            client = genai.Client(api_key=api_key)
            prompt_template = create_generation_prompt(topic, batch_size)
            
            # Start generation
            update_job(
                job_id,
                message="Generating flashcards...",
                progress=10
            )
            
            try:
                # Use streaming API instead of synchronous API
                stream = client.models.generate_content_stream(
                    model="gemini-2.0-flash-lite",
                    contents=prompt_template
                )
            except Exception as api_error:
                raise ValueError(f"AI generation error: {str(api_error)}")
            
            # Process streaming response
            buffer = ""  # Accumulate text for parsing
            cards_saved = 0
            processed_indices = set()  # Keep track of processed chunks
            
            update_job(
                job_id,
                message="Receiving AI response...",
                progress=20
            )
            
            # Process the stream
            for i, chunk in enumerate(stream):
                try:
                    # Skip empty chunks
                    if not chunk.text:
                        continue
                        
                    # Add chunk to buffer
                    buffer += chunk.text
                    
                    # Update progress based on incoming chunks (simulate progress)
                    if i % 5 == 0:  # Update progress every 5 chunks
                        progress = min(60, 20 + i)
                        update_job(
                            job_id,
                            progress=progress,
                            message=f"Receiving content from AI... ({len(buffer)} characters)"
                        )
                    
                    # Try to extract complete flashcards from the buffer
                    cards, remaining = extract_complete_flashcards(buffer)
                    buffer = remaining  # Keep unprocessed text
                    
                    # Process any complete cards found
                    if cards:
                        # Save cards to database
                        for card in cards:
                            # Add sample card for preview
                            add_sample_card(job_id, card)
                            
                            # Check if card already exists
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
                                cards_saved += 1
                        
                        # Commit batch
                        db.session.commit()
                        
                        # Update progress
                        update_job(
                            job_id,
                            progress=min(80, 60 + (cards_saved * 20 // batch_size)),
                            completed_cards=cards_saved,
                            message=f"Generated {cards_saved} flashcards so far..."
                        )
                except Exception as chunk_error:
                    print(f"Error processing chunk {i}: {chunk_error}")
                    continue  # Continue with next chunk
            
            # Process any remaining text in the buffer
            if buffer:
                update_job(
                    job_id,
                    message="Processing remaining content...",
                    progress=85
                )
                
                # Force parsing on the remaining buffer
                cards, _ = extract_complete_flashcards(buffer, force_parse=True)
                
                # Save any final cards
                for card in cards:
                    add_sample_card(job_id, card)
                    
                    # Check if card already exists
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
                        cards_saved += 1
                
                # Commit final batch
                db.session.commit()
                
                update_job(
                    job_id,
                    progress=95,
                    completed_cards=cards_saved,
                    message=f"Finalizing {cards_saved} flashcards..."
                )
                
            # Final update
            if cards_saved > 0:
                update_job(
                    job_id,
                    status=STATUS_COMPLETED,
                    progress=100,
                    completed_cards=cards_saved,
                    message=f"Completed! Generated {cards_saved} flashcards."
                )
            else:
                raise ValueError("No flashcards were generated. Please try a different topic or check the API.")
            
        except Exception as e:
            error_message = str(e)
            print(f"Error in background flashcard generation: {error_message}")
            print(traceback.format_exc())  # Add full stack trace for debugging
            
            update_job(
                job_id,
                status=STATUS_FAILED,
                message=f"Error: {error_message}"
            )
            
            # Only rollback if there's an active transaction
            try:
                db.session.rollback()
            except:
                # If rollback fails, we're likely not in a transaction
                pass

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
    """Parse generated text into structured flashcard data with better error handling"""
    flashcards = []
    flashcard_responses = text.split("question:")
    
    print(f"Found {len(flashcard_responses)-1} potential flashcards in response")
    
    for i, card_response in enumerate(flashcard_responses[1:]):  # Skip first empty split
        try:
            # Make sure all required parts are present before extracting
            if "correct:" not in card_response.lower():
                print(f"Missing 'correct:' in flashcard {i+1}")
                continue
                
            if "incorrect:" not in card_response.lower():
                print(f"Missing 'incorrect:' in flashcard {i+1}")
                continue
            
            correct_start = card_response.lower().index("correct:") + len("correct:")
            incorrect_start = card_response.lower().index("incorrect:") + len("incorrect:")
            
            question = card_response[:correct_start].replace("correct:", "").strip()
            correct_answer = card_response[correct_start:incorrect_start].replace("incorrect:", "").strip()
            incorrect_text = card_response[incorrect_start:]
            
            incorrect_answers = [
                ans.strip().split('**')[0].strip() # Remove any **text** markers
                for ans in incorrect_text.split(";")
                if ans and ans.strip()
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
            print(f"Error parsing flashcard {i+1}: {e}")
            # Continue to next card
            continue
        except Exception as e:
            print(f"Unexpected error parsing flashcard {i+1}: {e}")
            # Continue to next card
            continue

    print(f"Successfully parsed {len(flashcards)} flashcards")
    return flashcards
