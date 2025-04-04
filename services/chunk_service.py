import json
import traceback
import re
from google.genai import types
from models import FlashcardGenerator, db, Flashcards, ImportFile, ImportChunk, ImportFlashcard
from config import Config
from utils import clean_flashcard_text
from services.storage_service import ProcessingState
from flask import current_app
from services.fsrs_scheduler import get_current_time

def process_file_chunk_batch(client, file_key, chunk_index):
    """Process a single chunk of a file in batch mode"""
    state = ProcessingState.get_state(file_key)
    if not state or state['is_complete'] or chunk_index >= state['total_chunks']:
        return {'error': 'Invalid state or chunk index'}
    
    # Get the import file record
    import_file = ImportFile.query.filter_by(file_key=file_key).first()
    if not import_file:
        return {'error': 'Import file not found'}
    
    # Check if this chunk has already been processed and saved
    chunk = ImportChunk.query.filter_by(file_id=import_file.id, index=chunk_index).first()
    if not chunk:
        return {'error': f'Chunk {chunk_index} not found'}
    
    if chunk.is_saved:
        current_app.logger.info(f"Chunk {chunk_index} already processed and saved, skipping")
        return {
            'flashcards': [],
            'all_flashcards_count': ImportFlashcard.query.filter_by(file_id=import_file.id).count(),
            'chunk_index': chunk_index,
            'total_chunks': state['total_chunks'],
            'is_complete': state['is_complete'],
            'already_saved': True,
            'cards_saved': 0
        }
    
    # Get chunk content from database
    chunk_content = chunk.content
    if not chunk_content:
        return {'error': f'Cannot read chunk {chunk_index}'}
    
    # Log chunk size for debugging
    chunk_size = len(chunk_content)
    current_app.logger.info(f"Processing chunk {chunk_index} with {chunk_size} characters")
    
    # Check if chunk is too small
    if chunk_size < 50:
        current_app.logger.warning(f"Chunk {chunk_index} is too small ({chunk_size} chars), might not generate flashcards")
    
    # Initialize generator for this chunk
    generator = FlashcardGenerator(client)
    
    try:
        # Generate flashcards for this chunk using the multiple-choice format
        prompt = Config.generate_prompt_template(f"the following content: {chunk_content}", 
                                                batch_size=Config.DEFAULT_BATCH_SIZE)
        
        # Use the model from Config instead of hardcoding it
        current_app.logger.info(f"Using model: {Config.GEMINI_MODEL}")
        
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=types.Part.from_text(text=prompt),
            config=Config.GEMINI_CONFIG
        )
        
        # Log response details for debugging
        current_app.logger.info(f"Received response from Gemini API for chunk {chunk_index}")
        
        chunk_flashcards = []
        mc_data = []
        
        # Try to parse JSON response for multiple-choice format
        try:
            # Log the raw response for debugging
            current_app.logger.debug(f"Raw response text: {response.text}")
            
            response_text = response.text
            
            # Try to repair common JSON formatting issues
            repaired_json = repair_json(response_text)
            
            # Try to parse the JSON
            flashcards_data = json.loads(repaired_json)
            current_app.logger.info(f"Successfully parsed JSON response with {len(flashcards_data)} flashcards")
            
            # Format flashcards for compatibility with existing UI
            for card in flashcards_data:
                # Skip incomplete cards
                if not all(key in card for key in ['q', 'ca', 'ia']):
                    current_app.logger.warning(f"Skipping incomplete card: {card}")
                    continue
                
                # Format: Q: [question] | A: [correct_answer]
                formatted_card = f"Q: {card['q']} | A: {card['ca']}"
                chunk_flashcards.append(formatted_card)
                mc_data.append(card)
                
        except (json.JSONDecodeError, KeyError) as e:
            # Log the parsing error
            current_app.logger.error(f"Failed to parse JSON: {str(e)}")
            
            # Try extracting cards using regex as last resort
            current_app.logger.info("Attempting to extract cards using regex pattern matching")
            extracted_cards = extract_cards_from_text(response_text)
            
            if extracted_cards:
                current_app.logger.info(f"Successfully extracted {len(extracted_cards)} cards using pattern matching")
                mc_data = extracted_cards
                
                # Also format as standard flashcards
                for card in extracted_cards:
                    formatted_card = f"q: {card['q']} | ca: {card['ca']}"
                    chunk_flashcards.append(formatted_card)
            else:
                # Fallback to legacy format if JSON parsing fails
                raw_cards = response_text.split('\n')
                for card in raw_cards:
                    if 'q:' in card and '|' in card and 'a:' in card:
                        cleaned = clean_flashcard_text(card)
                        if cleaned:
                            chunk_flashcards.append(cleaned)
                
                current_app.logger.info(f"Fallback parsing found {len(chunk_flashcards)} flashcards")
        
        # Log results
        current_app.logger.info(f"Generated {len(chunk_flashcards)} flashcards for chunk {chunk_index}")
        
        # Store the multiple-choice data in the database
        if mc_data:
            # Store in database instead of memory
            for card_data in mc_data:
                new_card = ImportFlashcard(
                    file_id=import_file.id,
                    chunk_id=chunk.id,
                    question=card_data.get('q', ''),
                    correct_answer=card_data.get('ca', ''),
                    incorrect_answers=card_data.get('ia', [])
                )
                db.session.add(new_card)
            
            db.session.flush()
            
        # Update chunk as processed
        chunk.is_processed = True
        
        # Update file processing state
        import_file.current_index = chunk_index + 1
        
        # Check if all chunks are processed
        if import_file.current_index >= import_file.total_chunks:
            import_file.is_complete = True
        
        # NEW: Automatically save the flashcards to the database
        cards_saved = 0
        if import_file.deck_id:
            deck_id = import_file.deck_id
            current_app.logger.info(f"Auto-saving flashcards to deck {deck_id}")
            
            # Get current time for all cards to use same timestamp
            current_time = get_current_time()
            
            # Get cards for this chunk that haven't been saved yet
            unsaved_cards = ImportFlashcard.query.filter_by(
                file_id=import_file.id, 
                chunk_id=chunk.id,
                is_saved=False
            ).all()
            
            for card in unsaved_cards:
                # Skip incomplete cards
                if not card.question or not card.correct_answer:
                    continue
                
                # Ensure incorrect_answers is a list and limit to 3 items
                incorrect_answers = card.incorrect_answers or []
                if not isinstance(incorrect_answers, list):
                    incorrect_answers = [str(incorrect_answers)]
                incorrect_answers = incorrect_answers[:3]
                
                # Pad with empty answers if needed
                while len(incorrect_answers) < 3:
                    incorrect_answers.append(f"Incorrect answer {len(incorrect_answers) + 1}")
                
                # Create a new flashcard
                new_card = Flashcards(
                    question=card.question,
                    correct_answer=card.correct_answer,
                    incorrect_answers=incorrect_answers,
                    flashcard_deck_id=int(deck_id),
                    due_date=current_time,
                    state=0
                )
                
                # Initialize FSRS state for the new card
                new_card.init_fsrs_state()
                
                # Add to session
                db.session.add(new_card)
                
                # Mark the import flashcard as saved
                card.is_saved = True
                
                cards_saved += 1
            
            # Mark the chunk as saved if any cards were saved
            if cards_saved > 0:
                chunk.is_saved = True
                chunk.cards_saved = cards_saved
                
                # Update the total saved cards count
                import_file.total_saved_cards += cards_saved
                
                # Clean up saved flashcards since they're now in the main Flashcards table
                cleanup_saved_flashcards(chunk.id)
        
        # Commit all database changes
        db.session.commit()
        
        # Return processing results
        return {
            'flashcards': chunk_flashcards,
            'all_flashcards_count': ImportFlashcard.query.filter_by(file_id=import_file.id).count(),
            'chunk_index': chunk_index,
            'total_chunks': import_file.total_chunks,
            'is_complete': import_file.is_complete,
            'has_mc_data': len(mc_data) > 0,
            'cards_saved': cards_saved,
            'total_saved_cards': import_file.total_saved_cards
        }
        
    except Exception as e:
        error_msg = f"Error processing chunk {chunk_index}: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        db.session.rollback()
        return {'error': error_msg}

def cleanup_saved_flashcards(chunk_id):
    """Delete ImportFlashcard records that have been saved to the main Flashcards table"""
    try:
        # Find saved flashcards for this chunk
        saved_cards = ImportFlashcard.query.filter_by(
            chunk_id=chunk_id,
            is_saved=True
        ).all()
        
        # Delete them to save space
        for card in saved_cards:
            db.session.delete(card)
            
        current_app.logger.info(f"Cleaned up {len(saved_cards)} saved flashcards for chunk {chunk_id}")
        
    except Exception as e:
        current_app.logger.error(f"Error cleaning up saved flashcards: {str(e)}")

def cleanup_all_flashcards(file_key):
    """Delete all ImportFlashcard records for a file after import is complete"""
    try:
        import_file = ImportFile.query.filter_by(file_key=file_key).first()
        if not import_file:
            return False
            
        # Get the count of flashcards for logging
        count = ImportFlashcard.query.filter_by(file_id=import_file.id).count()
        
        # Delete all flashcards for this file
        ImportFlashcard.query.filter_by(file_id=import_file.id).delete()
        
        # Commit the changes
        db.session.commit()
        
        current_app.logger.info(f"Cleaned up {count} flashcards for file {file_key}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error cleaning up all flashcards: {str(e)}")
        db.session.rollback()
        return False

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
    # This is a simplified regex and might need adjustment
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

def get_file_state(file_key):
    """Get current processing state for a file"""
    state = ProcessingState.get_state(file_key)
    if not state:
        return {'error': 'Invalid file key'}
    
    all_flashcards = ProcessingState.get_all_flashcards(file_key)
    
    return {
        'total_chunks': state['total_chunks'],
        'processed_chunks': len(state['processed_chunks']),
        'current_index': state['current_index'],
        'flashcard_count': len(all_flashcards),
        'is_complete': state['is_complete'],
        'next_chunk': state['current_index'] if state['current_index'] < state['total_chunks'] else None
    }
