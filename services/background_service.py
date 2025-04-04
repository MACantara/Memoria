import threading
import time
import uuid
from datetime import datetime
from flask import current_app

class TaskStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'

class ImportTask:
    def __init__(self, file_key, filename, deck_id, deck_name, user_id):
        self.id = str(uuid.uuid4())
        self.file_key = file_key
        self.filename = filename
        self.deck_id = deck_id
        self.deck_name = deck_name
        self.user_id = user_id
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.total_chunks = 0
        self.current_chunk = 0
        self.total_cards = 0
        self.saved_cards = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.completed_at = None
        self.error = None

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
        return self
        
    def to_dict(self):
        return {
            'id': self.id,
            'file_key': self.file_key,
            'filename': self.filename,
            'deck_id': self.deck_id,
            'deck_name': self.deck_name,
            'status': self.status,
            'progress': self.progress,
            'total_chunks': self.total_chunks,
            'current_chunk': self.current_chunk,
            'total_cards': self.total_cards,
            'saved_cards': self.saved_cards,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error
        }

# In-memory storage for background tasks - in production this should use Redis or a database
tasks = {}
tasks_by_user = {}
tasks_lock = threading.Lock()

def get_user_tasks(user_id):
    """Get all tasks for a user"""
    with tasks_lock:
        return [task for task in tasks.values() if task.user_id == user_id]

def get_task(task_id):
    """Get a specific task by ID"""
    with tasks_lock:
        return tasks.get(task_id)

def get_task_by_file_key(file_key):
    """Get a task by file key"""
    with tasks_lock:
        for task in tasks.values():
            if task.file_key == file_key:
                return task
    return None

def register_task(task):
    """Register a new task"""
    with tasks_lock:
        tasks[task.id] = task
        if task.user_id not in tasks_by_user:
            tasks_by_user[task.user_id] = []
        tasks_by_user[task.user_id].append(task.id)
    return task

def update_task(task_id, **kwargs):
    """Update a task's status and progress"""
    task = get_task(task_id)
    if task:
        with tasks_lock:
            task.update(**kwargs)
            # If task is completed or failed, set the completion time
            if kwargs.get('status') in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = datetime.now()
    return task

def cleanup_old_tasks(age_hours=24):
    """Remove old completed tasks"""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(hours=age_hours)
    
    with tasks_lock:
        to_remove = []
        for task_id, task in tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and task.updated_at < cutoff:
                to_remove.append(task_id)
                
        for task_id in to_remove:
            task = tasks.pop(task_id)
            if task.user_id in tasks_by_user:
                if task_id in tasks_by_user[task.user_id]:
                    tasks_by_user[task.user_id].remove(task_id)

def process_chunk(task_id, app, gemini_client, file_key, chunk_index):
    """Process a single chunk in the background"""
    from services.chunk_service import process_file_chunk_batch
    
    task = get_task(task_id)
    if not task:
        return
    
    # Create an application context for this thread
    with app.app_context():
        try:
            # Update task status
            update_task(task_id, status=TaskStatus.RUNNING)
            
            # Process the chunk
            result = process_file_chunk_batch(gemini_client, file_key, chunk_index)
            
            if 'error' in result:
                update_task(
                    task_id, 
                    error=result['error'],
                    status=TaskStatus.FAILED
                )
                return
            
            # Update progress
            progress = int((result['chunk_index'] + 1) / result['total_chunks'] * 100)
            update_task(
                task_id,
                progress=progress,
                current_chunk=result['chunk_index'] + 1,
                total_chunks=result['total_chunks'],
                saved_cards=result.get('total_saved_cards', 0)
            )
            
            # If not complete, process the next chunk
            if not result.get('is_complete'):
                # Schedule the next chunk
                next_chunk = result['chunk_index'] + 1
                thread = threading.Thread(
                    target=process_chunk,
                    args=(task_id, app, gemini_client, file_key, next_chunk)
                )
                thread.daemon = True
                thread.start()
            else:
                # Update as completed
                update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    progress=100
                )
        except Exception as e:
            app.logger.error(f"Background task error: {str(e)}")
            update_task(
                task_id,
                status=TaskStatus.FAILED,
                error=str(e)
            )

def start_processing(app, gemini_client, file_key, filename, deck_id, deck_name, user_id):
    """Start background processing of a file"""
    # Create a new task
    task = ImportTask(file_key, filename, deck_id, deck_name, user_id)
    register_task(task)
    
    # Start processing the first chunk
    thread = threading.Thread(
        target=process_chunk,
        args=(task.id, app, gemini_client, file_key, 0)
    )
    thread.daemon = True
    thread.start()
    
    return task.id
