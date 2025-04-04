import hashlib
import time
from flask import session, has_request_context, current_app, g
from flask_login import current_user

from config import Config
from services.file_service import FileProcessor
from utils import chunk_text
from models import db, ImportFile, ImportChunk, ImportFlashcard

class ProcessingState:
    """Store processing state in database between requests"""
    
    @staticmethod
    def get_file_key(filepath):
        """Generate a unique key for a file"""
        return hashlib.md5(filepath.encode('utf-8')).hexdigest()
    
    @staticmethod
    def init_file_state(filepath):
        """Initialize processing state for a file in the database"""
        try:
            # Create a unique key for this file
            file_key = ProcessingState.get_file_key(filepath)
            
            # Check if this file is already being processed
            existing_file = ImportFile.query.filter_by(file_key=file_key).first()
            if existing_file:
                # Delete the existing file and its chunks to start fresh
                db.session.delete(existing_file)
                db.session.commit()
            
            # Read content and divide into chunks
            content = FileProcessor.read_content(filepath)
            chunks = chunk_text(content)
            
            # Create a new import file record
            import_file = ImportFile(
                file_key=file_key,
                filename=filepath.split('/')[-1],
                user_id=current_user.id,
                total_chunks=len(chunks),
                current_index=0,
                is_complete=False
            )
            
            db.session.add(import_file)
            db.session.flush()  # Get the id without committing
            
            # Store all chunks in the database
            for i, chunk_content in enumerate(chunks):
                chunk = ImportChunk(
                    file_id=import_file.id,
                    index=i,
                    content=chunk_content,
                    is_processed=False,
                    is_saved=False
                )
                db.session.add(chunk)
            
            # Commit all changes
            db.session.commit()
            
            return file_key
            
        except Exception as e:
            current_app.logger.error(f"Error in init_file_state: {str(e)}")
            db.session.rollback()
            raise
    
    @staticmethod
    def get_state(file_key):
        """Get processing state for a file from the database"""
        import_file = ImportFile.query.filter_by(file_key=file_key).first()
        
        if not import_file:
            return None
            
        # Convert to dictionary format for backward compatibility
        state = {
            'file_key': import_file.file_key,
            'total_chunks': import_file.total_chunks,
            'processed_chunks': [c.index for c in import_file.chunks if c.is_processed],
            'saved_chunks': [c.index for c in import_file.chunks if c.is_saved],
            'total_saved_cards': import_file.total_saved_cards,
            'current_index': import_file.current_index,
            'is_complete': import_file.is_complete,
            'last_updated': import_file.updated_at.timestamp() if import_file.updated_at else time.time(),
            'deck_id': import_file.deck_id
        }
        
        return state
    
    @staticmethod
    def get_chunk(file_key, chunk_index):
        """Get a specific chunk content from the database"""
        import_file = ImportFile.query.filter_by(file_key=file_key).first()
        if not import_file:
            return None
        
        chunk = ImportChunk.query.filter_by(file_id=import_file.id, index=chunk_index).first()
        if not chunk:
            return None
            
        return chunk.content
    
    @staticmethod
    def update_state(file_key, updates):
        """Update processing state for a file in the database"""
        import_file = ImportFile.query.filter_by(file_key=file_key).first()
        if not import_file:
            return False
            
        # Update import file record
        for key, value in updates.items():
            if key == 'processed_chunks':
                # Skip this, it's tracked at the chunk level
                continue
            elif key == 'saved_chunks':
                # Skip this, it's tracked at the chunk level
                continue
            elif key == 'current_index':
                import_file.current_index = value
            elif key == 'is_complete':
                import_file.is_complete = value
            elif key == 'deck_id':
                import_file.deck_id = value
            elif key == 'total_saved_cards':
                import_file.total_saved_cards = value
                
        # Commit changes
        db.session.commit()
            
        return True
    
    @staticmethod
    def get_all_flashcards(file_key):
        """Get all flashcards for a file in simple format"""
        import_file = ImportFile.query.filter_by(file_key=file_key).first()
        if not import_file:
            return []
            
        # Get all flashcards for this file and format them as strings
        flashcards = ImportFlashcard.query.filter_by(file_id=import_file.id).all()
        
        # Format as "Q: question | A: answer"
        formatted_cards = [f"Q: {card.question} | A: {card.correct_answer}" for card in flashcards]
            
        return formatted_cards
    
    @staticmethod
    def append_flashcards(file_key, new_flashcards):
        """
        Append text-formatted flashcards - this is kept for backward compatibility
        but doesn't actually store the data since we now use the MC format
        """
        # This is now a no-op since we use the MC format exclusively
        return True
    
    @staticmethod
    def get_mc_flashcards(file_key):
        """Get all multiple-choice flashcards for a file"""
        import_file = ImportFile.query.filter_by(file_key=file_key).first()
        if not import_file:
            return []
            
        # Get all flashcards for this file
        flashcards = ImportFlashcard.query.filter_by(file_id=import_file.id).all()
        
        # Format in the MC format
        mc_cards = []
        for card in flashcards:
            mc_cards.append({
                'q': card.question,
                'ca': card.correct_answer,
                'ia': card.incorrect_answers or []
            })
            
        return mc_cards
    
    @staticmethod
    def append_mc_flashcards(file_key, new_mc_flashcards):
        """Append multiple-choice flashcards to the database"""
        import_file = ImportFile.query.filter_by(file_key=file_key).first()
        if not import_file:
            return False
            
        # Get the current chunk being processed
        chunk = ImportChunk.query.filter_by(
            file_id=import_file.id, 
            index=import_file.current_index
        ).first()
        
        if not chunk:
            return False
            
        # Add each flashcard to the database
        for card_data in new_mc_flashcards:
            flashcard = ImportFlashcard(
                file_id=import_file.id,
                chunk_id=chunk.id,
                question=card_data.get('q', ''),
                correct_answer=card_data.get('ca', ''),
                incorrect_answers=card_data.get('ia', []),
                is_saved=False
            )
            db.session.add(flashcard)
            
        # Commit changes
        db.session.commit()
        
        return True
    
    @staticmethod
    def get_saved_flashcards_count(file_key):
        """Get count of flashcards already saved to the database"""
        import_file = ImportFile.query.filter_by(file_key=file_key).first()
        if not import_file:
            return 0
        
        return import_file.total_saved_cards
    
    @staticmethod
    def mark_chunk_saved(file_key, chunk_index, cards_saved):
        """Mark a chunk as saved to the database"""
        import_file = ImportFile.query.filter_by(file_key=file_key).first()
        if not import_file:
            return False
            
        # Get the chunk and mark it as saved
        chunk = ImportChunk.query.filter_by(file_id=import_file.id, index=chunk_index).first()
        if not chunk:
            return False
            
        chunk.is_saved = True
        chunk.cards_saved = cards_saved
        
        # Update the total saved cards count
        import_file.total_saved_cards += cards_saved
        
        # Commit changes
        db.session.commit()
        
        return True
    
    @staticmethod
    def cleanup_old_states(max_age=3600):  # 1 hour
        """Remove old processing states"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(seconds=max_age)
        
        # Find old import files
        old_files = ImportFile.query.filter(ImportFile.updated_at < cutoff_time).all()
        
        # Delete them
        for file in old_files:
            db.session.delete(file)  # This should cascade to chunks and flashcards
            
        # Commit changes
        db.session.commit()
