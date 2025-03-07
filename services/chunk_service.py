import json
import traceback
import re
from google.genai import types
from models import FlashcardGenerator
from config import Config
from utils import clean_flashcard_text
from services.storage_service import ProcessingState
from flask import current_app

def process_file_chunk_batch(client, file_key, chunk_index):
    """Process a single chunk of a file in batch mode"""
    state = ProcessingState.get_state(file_key)
    if not state or state['is_complete'] or chunk_index >= state['total_chunks']:
        return {'error': 'Invalid state or chunk index'}
    
    # Get chunk content
    chunk = ProcessingState.get_chunk(file_key, chunk_index)
    if not chunk:
        return {'error': f'Cannot read chunk {chunk_index}'}
    
    # Log chunk size for debugging
    chunk_size = len(chunk)
    current_app.logger.info(f"Processing chunk {chunk_index} with {chunk_size} characters")
    
    # Check if chunk is too small
    if chunk_size < 50:
        current_app.logger.warning(f"Chunk {chunk_index} is too small ({chunk_size} chars), might not generate flashcards")
    
    # Initialize generator for this chunk
    generator = FlashcardGenerator(client)
    
    try:
        # Generate flashcards for this chunk using the multiple-choice format
        prompt = Config.generate_prompt_template(f"the following content: {chunk}", 
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
        
        # Store the multiple-choice data if available
        if mc_data:
            ProcessingState.append_mc_flashcards(file_key, mc_data)
            
        # Also store the formatted cards for backward compatibility
        ProcessingState.append_flashcards(file_key, chunk_flashcards)
        
        # Update processing state
        state['processed_chunks'].append(chunk_index)
        state['current_index'] = chunk_index + 1
        
        if len(state['processed_chunks']) == state['total_chunks']:
            state['is_complete'] = True
        
        ProcessingState.update_state(file_key, state)
        
        # Get total flashcards count
        all_flashcards = ProcessingState.get_all_flashcards(file_key)
        
        return {
            'flashcards': chunk_flashcards,
            'all_flashcards_count': len(all_flashcards),
            'chunk_index': chunk_index,
            'total_chunks': state['total_chunks'],
            'is_complete': state['is_complete'],
            'has_mc_data': len(mc_data) > 0
        }
        
    except Exception as e:
        error_msg = f"Error processing chunk {chunk_index}: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return {'error': error_msg}

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
