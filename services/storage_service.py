import os
import hashlib
import time
import pickle
import shutil
from flask import session, has_request_context

from config import Config
from services.file_service import FileProcessor
from utils import chunk_text

class ProcessingState:
    """Store processing state between requests"""
    # Class-level dictionary to store states in memory when Flask session is not available
    _memory_states = {}
    
    @staticmethod
    def get_file_key(filepath):
        """Generate a unique key for a file"""
        return hashlib.md5(filepath.encode('utf-8')).hexdigest()
    
    @staticmethod
    def init_file_state(filepath):
        """Initialize processing state for a file"""
        try:
            # Create a unique directory for this file processing
            file_key = ProcessingState.get_file_key(filepath)
            state_dir = os.path.join(Config.UPLOAD_FOLDER, file_key)
            os.makedirs(state_dir, exist_ok=True)
            
            # Read content and divide into chunks
            content = FileProcessor.read_content(filepath)
            chunks = chunk_text(content)
            
            # Store chunks in separate files
            chunks_dir = os.path.join(state_dir, "chunks")
            os.makedirs(chunks_dir, exist_ok=True)
            
            for i, chunk in enumerate(chunks):
                chunk_file = os.path.join(chunks_dir, f"chunk_{i}.txt")
                with open(chunk_file, 'w', encoding='utf-8') as f:
                    f.write(chunk)
            
            # Create a state object
            state = {
                'file_key': file_key,
                'state_dir': state_dir,
                'total_chunks': len(chunks),
                'processed_chunks': [],
                'current_index': 0,
                'is_complete': False,
                'last_updated': time.time()
            }
            
            # Store state - either in Flask session or in memory
            if has_request_context():
                try:
                    session[file_key] = state
                except RuntimeError:
                    # No secret key or session not available - use memory storage instead
                    ProcessingState._memory_states[file_key] = state
            else:
                # We're not in a Flask request context (e.g., desktop app)
                ProcessingState._memory_states[file_key] = state
            
            # Also save state to disk for persistence
            state_file = os.path.join(state_dir, "state.pkl")
            with open(state_file, 'wb') as f:
                pickle.dump(state, f)
            
            return file_key
        except Exception as e:
            print(f"Error in init_file_state: {str(e)}")
            # Clean up any partial files
            if 'state_dir' in locals() and os.path.exists(state_dir):
                shutil.rmtree(state_dir, ignore_errors=True)
            raise
    
    @staticmethod
    def get_state(file_key):
        """Get processing state for a file"""
        # Try getting state from session, memory, or disk
        
        # First try Flask session if in a request context
        if has_request_context():
            try:
                state = session.get(file_key)
                if state:
                    return state
            except RuntimeError:
                # Session not available
                pass
                
        # Next try in-memory dictionary
        if file_key in ProcessingState._memory_states:
            return ProcessingState._memory_states[file_key]
            
        # Finally try loading from disk
        try:
            state_file = os.path.join(Config.UPLOAD_FOLDER, file_key, "state.pkl")
            if os.path.exists(state_file):
                with open(state_file, 'rb') as f:
                    return pickle.load(f)
        except:
            pass
            
        return None
    
    @staticmethod
    def get_chunk(file_key, chunk_index):
        """Get a specific chunk content"""
        state = ProcessingState.get_state(file_key)
        if not state:
            return None
        
        chunk_file = os.path.join(state['state_dir'], "chunks", f"chunk_{chunk_index}.txt")
        if not os.path.exists(chunk_file):
            return None
            
        with open(chunk_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def update_state(file_key, updates):
        """Update processing state for a file"""
        state = ProcessingState.get_state(file_key)
        if not state:
            return False
            
        # Handle flashcards separately to prevent session bloat
        if 'all_flashcards' in updates:
            flashcards = updates.pop('all_flashcards')
            # Save flashcards to file
            flashcards_file = os.path.join(state['state_dir'], "flashcards.pkl")
            with open(flashcards_file, 'wb') as f:
                pickle.dump(flashcards, f)
                
        # Update other state properties
        for key, value in updates.items():
            state[key] = value
            
        state['last_updated'] = time.time()
        
        # Update state in all storage locations
        if has_request_context():
            try:
                session[file_key] = state
            except RuntimeError:
                ProcessingState._memory_states[file_key] = state
        else:
            ProcessingState._memory_states[file_key] = state
            
        # Always save to disk for persistence
        try:
            state_file = os.path.join(state['state_dir'], "state.pkl")
            with open(state_file, 'wb') as f:
                pickle.dump(state, f)
        except:
            pass
            
        return True
    
    @staticmethod
    def get_all_flashcards(file_key):
        """Get all flashcards for a file"""
        state = ProcessingState.get_state(file_key)
        if not state:
            return []
            
        flashcards_file = os.path.join(state['state_dir'], "flashcards.pkl")
        if os.path.exists(flashcards_file):
            with open(flashcards_file, 'rb') as f:
                return pickle.load(f)
        return []
    
    @staticmethod
    def append_flashcards(file_key, new_flashcards):
        """Append new flashcards to existing ones"""
        state = ProcessingState.get_state(file_key)
        if not state:
            return False
            
        current = ProcessingState.get_all_flashcards(file_key)
        updated = current + new_flashcards
        
        flashcards_file = os.path.join(state['state_dir'], "flashcards.pkl")
        with open(flashcards_file, 'wb') as f:
            pickle.dump(updated, f)
        
        return True
    
    @staticmethod
    def append_mc_flashcards(file_key, new_mc_flashcards):
        """Append multiple-choice flashcards to existing ones"""
        state = ProcessingState.get_state(file_key)
        if not state:
            return False
            
        mc_file = os.path.join(state['state_dir'], "mc_flashcards.pkl")
        
        current = []
        if os.path.exists(mc_file):
            with open(mc_file, 'rb') as f:
                current = pickle.load(f)
                
        updated = current + new_mc_flashcards
        
        with open(mc_file, 'wb') as f:
            pickle.dump(updated, f)
        
        return True
    
    @staticmethod
    def get_mc_flashcards(file_key):
        """Get all multiple-choice flashcards for a file"""
        state = ProcessingState.get_state(file_key)
        if not state:
            return []
            
        mc_file = os.path.join(state['state_dir'], "mc_flashcards.pkl")
        if os.path.exists(mc_file):
            with open(mc_file, 'rb') as f:
                return pickle.load(f)
        return []
    
    @staticmethod
    def cleanup_old_states(max_age=3600):  # 1 hour
        """Remove old processing states"""
        now = time.time()
        
        # Clean up memory states
        keys_to_remove = []
        for key, state in ProcessingState._memory_states.items():
            if now - state.get('last_updated', 0) > max_age:
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            if key in ProcessingState._memory_states:
                del ProcessingState._memory_states[key]
        
        # Clean up Flask session if available
        if has_request_context():
            try:
                session_keys = list(session.keys())
                for key in session_keys:
                    if isinstance(session.get(key), dict) and 'last_updated' in session[key]:
                        if now - session[key]['last_updated'] > max_age:
                            del session[key]
            except RuntimeError:
                pass
                
        # Clean up disk storage
        if not os.path.exists(Config.UPLOAD_FOLDER):
            return
            
        for file_key in os.listdir(Config.UPLOAD_FOLDER):
            state_dir = os.path.join(Config.UPLOAD_FOLDER, file_key)
            if not os.path.isdir(state_dir):
                continue
                
            state_file = os.path.join(state_dir, "state.pkl")
            if not os.path.exists(state_file):
                # No state file, remove directory
                shutil.rmtree(state_dir, ignore_errors=True)
                continue
                
            try:
                with open(state_file, 'rb') as f:
                    state = pickle.load(f)
                    
                if now - state.get('last_updated', 0) > max_age:
                    # Too old, remove directory
                    shutil.rmtree(state_dir, ignore_errors=True)
            except:
                # Can't read state, remove directory
                shutil.rmtree(state_dir, ignore_errors=True)
