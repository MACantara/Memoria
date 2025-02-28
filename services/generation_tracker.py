"""
Service for tracking flashcard generation progress
Uses an in-memory store that can be queried by the frontend
"""
import time
import uuid
from threading import Lock

# In-memory store for generation jobs
# Format: { job_id: {status, progress, message, cards, etc} }
_generation_jobs = {}
_lock = Lock()

# Job status constants
STATUS_PENDING = "pending"
STATUS_GENERATING = "generating"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

def create_job(deck_id=None, topic=None):
    """Create a new tracking job for flashcard generation"""
    job_id = str(uuid.uuid4())
    
    with _lock:
        _generation_jobs[job_id] = {
            "id": job_id,
            "deck_id": deck_id,
            "topic": topic,
            "status": STATUS_PENDING,
            "progress": 0,
            "start_time": time.time(),
            "updated_time": time.time(),
            "message": "Initializing...",
            "total_cards": 0,
            "completed_cards": 0,
            "sample_cards": [],  # Store a few sample cards for preview
            "redirect_url": None
        }
    
    # Clean up old jobs (remove jobs older than 2 hours)
    cleanup_old_jobs()
    
    return job_id

def update_job(job_id, **kwargs):
    """Update job status and information"""
    with _lock:
        if job_id not in _generation_jobs:
            return False
        
        for key, value in kwargs.items():
            if key in _generation_jobs[job_id]:
                _generation_jobs[job_id][key] = value
                
        # Always update the last updated time
        _generation_jobs[job_id]["updated_time"] = time.time()
        
    return True

def get_job(job_id):
    """Get job status and information"""
    with _lock:
        return _generation_jobs.get(job_id, {}).copy()

def add_sample_card(job_id, card):
    """Add a sample card to the job (for preview)"""
    with _lock:
        if job_id not in _generation_jobs:
            return False
            
        # Keep only up to 5 sample cards
        samples = _generation_jobs[job_id].get("sample_cards", [])
        if len(samples) >= 5:
            samples.pop(0)  # Remove oldest
            
        # Add new sample
        samples.append({
            "question": card.get("question", "")[:75] + "..." if len(card.get("question", "")) > 75 else card.get("question", ""),
            "answer": card.get("correct_answer", "")[:50] + "..." if len(card.get("correct_answer", "")) > 50 else card.get("correct_answer", ""),
        })
        
        _generation_jobs[job_id]["sample_cards"] = samples
        
    return True

def cleanup_old_jobs():
    """Remove old jobs to prevent memory leaks"""
    current_time = time.time()
    with _lock:
        job_ids = list(_generation_jobs.keys())
        for job_id in job_ids:
            # Remove jobs older than 2 hours
            if current_time - _generation_jobs[job_id]["start_time"] > 7200:
                del _generation_jobs[job_id]
