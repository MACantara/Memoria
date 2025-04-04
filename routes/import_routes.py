from flask import Blueprint, request, jsonify, current_app
import os
import uuid
from werkzeug.utils import secure_filename

from config import Config
from utils import allowed_file
from models import db, FlashcardDecks, Flashcards
from services.file_service import FileProcessor
from services.storage_service import ProcessingState
from services.chunk_service import process_file_chunk_batch, get_file_state

# Create Blueprint
import_bp = Blueprint('import', __name__, url_prefix='/import')

@import_bp.route('/upload-file', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Make sure deck_id is provided
        deck_id = request.form.get('deck_id')
        if not deck_id:
            return jsonify({'error': 'Deck ID is required'}), 400

        # Create a safe filename and ensure upload directory exists
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        
        # Ensure upload directory exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Save file safely
        try:
            file.save(filepath)
        except Exception as e:
            current_app.logger.error(f"File save error: {str(e)}")
            return jsonify({'error': 'Failed to save file'}), 500
        
        # Initialize processing state
        file_key = ProcessingState.init_file_state(filepath)
        state = ProcessingState.get_state(file_key)
        
        # Store deck_id with file_key for later use
        state['deck_id'] = deck_id
        ProcessingState.update_state(file_key, state)
        
        # Clean up old processing states
        ProcessingState.cleanup_old_states()
        
        return jsonify({
            'success': True, 
            'file_key': file_key, 
            'filename': filename,
            'total_chunks': state['total_chunks']
        })
        
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@import_bp.route('/generate-chunk', methods=['POST'])
def generate_chunk():
    """Generate flashcards from a specific chunk of a file"""
    try:
        data = request.get_json()
        file_key = data.get('file_key')
        chunk_index = data.get('chunk_index')
        
        if not file_key:
            return jsonify({'error': 'File key is required'}), 400
        
        state = ProcessingState.get_state(file_key)
        if not state:
            return jsonify({'error': 'Invalid file key'}), 400
        
        if chunk_index is None:
            chunk_index = state['current_index']
        
        if chunk_index >= state['total_chunks']:
            return jsonify({
                'message': 'All chunks processed',
                'is_complete': True,
                'total_saved_cards': state.get('total_saved_cards', 0)
            })
        
        # Use the processor for generating and auto-saving flashcards from chunks
        result = process_file_chunk_batch(current_app.gemini_client, file_key, chunk_index)
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in generate_chunk: {str(e)}")
        return jsonify({'error': str(e)}), 500

@import_bp.route('/file-state', methods=['GET'])
def file_state():
    """Get current processing state for a file"""
    file_key = request.args.get('file_key')
    
    if not file_key:
        return jsonify({'error': 'File key is required'}), 400
    
    result = get_file_state(file_key)

    # Add the count of saved cards to the response
    state = ProcessingState.get_state(file_key)
    if state:
        result['total_saved_cards'] = state.get('total_saved_cards', 0)
        result['saved_chunks'] = state.get('saved_chunks', [])
    
    return jsonify(result)

@import_bp.route('/all-file-flashcards', methods=['GET'])
def all_file_flashcards():
    """Get all flashcards for a file"""
    file_key = request.args.get('file_key')
    format_type = request.args.get('format', 'standard')  # 'standard' or 'mc' (multiple-choice)
    
    if not file_key:
        return jsonify({'error': 'File key is required'}), 400
    
    # Get saved cards count
    state = ProcessingState.get_state(file_key)
    total_saved_cards = state.get('total_saved_cards', 0) if state else 0
    
    if format_type == 'mc':
        # Return multiple-choice format if requested
        mc_flashcards = ProcessingState.get_mc_flashcards(file_key)
        return jsonify({
            'flashcards': ProcessingState.get_all_flashcards(file_key),  # For backward compatibility
            'mc_flashcards': mc_flashcards,
            'count': len(mc_flashcards),
            'total_saved_cards': total_saved_cards
        })
    else:
        # Return standard format by default
        all_flashcards = ProcessingState.get_all_flashcards(file_key)
        return jsonify({
            'flashcards': all_flashcards,
            'count': len(all_flashcards),
            'total_saved_cards': total_saved_cards
        })

@import_bp.route('/save-to-deck', methods=['POST'])
def save_to_deck():
    """
    Manual save endpoint - only used for backward compatibility or 
    if auto-save fails for some reason
    """
    try:
        data = request.get_json()
        file_key = data.get('file_key')
        deck_id = data.get('deck_id')
        flashcards = data.get('flashcards', [])
        
        if not file_key:
            return jsonify({'error': 'File key is required'}), 400
            
        if not deck_id:
            return jsonify({'error': 'Deck ID is required'}), 400
            
        # No flashcards provided, try to use all from file
        if not flashcards:
            flashcards = ProcessingState.get_mc_flashcards(file_key)
        
        if not flashcards:
            return jsonify({'error': 'No flashcards found for this file'}), 400
            
        # Get state to check if we've already saved cards
        state = ProcessingState.get_state(file_key)
        existing_count = state.get('total_saved_cards', 0) if state else 0
        
        if existing_count > 0:
            current_app.logger.info(f"Already saved {existing_count} cards, adding only additional cards")
        
        # Save each flashcard to the database
        cards_added = 0
        # Get current time for all cards to use same timestamp
        from services.fsrs_scheduler import get_current_time
        current_time = get_current_time()
        
        for card in flashcards:
            # Extract and validate required fields
            question = card.get('q', '')
            correct_answer = card.get('ca', '')
            incorrect_answers = card.get('ia', [])
            
            # Skip incomplete cards
            if not question or not correct_answer:
                current_app.logger.warning(f"Skipping incomplete card: {card}")
                continue
            
            # Ensure incorrect_answers is a list and limit to 3 items
            if not isinstance(incorrect_answers, list):
                incorrect_answers = [str(incorrect_answers)]
            incorrect_answers = incorrect_answers[:3]
            
            # Pad with empty answers if needed
            while len(incorrect_answers) < 3:
                incorrect_answers.append(f"Incorrect answer {len(incorrect_answers) + 1}")
            
            # Create a new flashcard
            new_card = Flashcards(
                question=question,
                correct_answer=correct_answer,
                incorrect_answers=incorrect_answers,
                flashcard_deck_id=int(deck_id),
                due_date=current_time,
                state=0
            )
            
            # Initialize FSRS state for the new card
            new_card.init_fsrs_state()
            
            # Add to session
            db.session.add(new_card)
            cards_added += 1
        
        # Commit all changes at once
        db.session.commit()
        current_app.logger.info(f"Added {cards_added} flashcards to deck {deck_id}")
        
        # Update total saved count in state
        if state:
            state['total_saved_cards'] = existing_count + cards_added
            ProcessingState.update_state(file_key, state)
        
        return jsonify({
            'success': True,
            'message': f'Added {cards_added} flashcards to deck',
            'count': cards_added,
            'total_saved_cards': existing_count + cards_added
        })
        
    except Exception as e:
        current_app.logger.error(f"Error saving flashcards to deck: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Failed to save flashcards to deck: {str(e)}'}), 500

# Add a new route to check saved status
@import_bp.route('/saved-status', methods=['GET'])
def get_saved_status():
    """Get the saved status for a file processing job"""
    file_key = request.args.get('file_key')
    
    if not file_key:
        return jsonify({'error': 'File key is required'}), 400
    
    state = ProcessingState.get_state(file_key)
    if not state:
        return jsonify({'error': 'Invalid file key'}), 400
    
    # Check if all chunks have been processed and saved
    total_chunks = state.get('total_chunks', 0)
    saved_chunks = state.get('saved_chunks', [])
    is_complete = state.get('is_complete', False)
    total_saved_cards = state.get('total_saved_cards', 0)
    
    # Calculate percentage complete for saving
    save_progress = 0
    if total_chunks > 0:
        save_progress = int(len(saved_chunks) / total_chunks * 100)
    
    return jsonify({
        'file_key': file_key,
        'total_chunks': total_chunks,
        'saved_chunks': len(saved_chunks),
        'saved_chunks_list': saved_chunks,
        'save_progress': save_progress,
        'is_complete': is_complete,
        'total_saved_cards': total_saved_cards,
        'fully_saved': len(saved_chunks) == total_chunks and is_complete,
        'deck_id': state.get('deck_id')
    })
