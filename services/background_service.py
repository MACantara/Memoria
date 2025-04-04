import threading
import time
import uuid
from datetime import datetime
from flask import current_app

from models import db, ImportTask

class TaskStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'

# Thread lock for preventing race conditions
task_lock = threading.Lock()

def get_user_tasks(user_id):
    """Get all tasks for a user from the database"""
    return ImportTask.query.filter_by(user_id=user_id).order_by(
        ImportTask.updated_at.desc()
    ).all()

def get_task(task_id):
    """Get a specific task by ID from the database"""
    return ImportTask.query.get(task_id)

def get_task_by_file_key(file_key):
    """Get a task by file key from the database"""
    return ImportTask.query.filter_by(file_key=file_key).first()

def register_task(file_key, filename, deck_id, deck_name, user_id):
    """Register a new task in the database"""
    with task_lock:
        # Create a new task with a UUID
        task_id = str(uuid.uuid4())
        task = ImportTask(
            id=task_id,
            file_key=file_key,
            filename=filename,
            deck_id=deck_id,
            deck_name=deck_name,
            user_id=user_id,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add to database
        db.session.add(task)
        db.session.commit()
        
    return task_id

def update_task(task_id, **kwargs):
    """Update a task's status and progress in the database"""
    with task_lock:
        task = ImportTask.query.get(task_id)
        if not task:
            return None
            
        # Update fields
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
                
        # Update timestamps
        task.updated_at = datetime.utcnow()
        
        # Set completion time if task is completed or failed
        if kwargs.get('status') in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task.completed_at = datetime.utcnow()
            
        # Save changes
        db.session.commit()
        
    return task

def cleanup_old_tasks(age_hours=24):
    """Remove old completed tasks from the database"""
    from datetime import timedelta
    with task_lock:
        cutoff_time = datetime.utcnow() - timedelta(hours=age_hours)
        
        # Find old completed or failed tasks
        old_tasks = ImportTask.query.filter(
            ImportTask.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED]),
            ImportTask.updated_at < cutoff_time
        ).all()
        
        # Delete them
        for task in old_tasks:
            db.session.delete(task)
            
        # Commit changes
        db.session.commit()
        
        return len(old_tasks)

def process_chunk(task_id, app, gemini_client, file_key, chunk_index):
    """Process a single chunk in the background"""
    from services.chunk_service import process_file_chunk_batch
    
    # Create an application context for this thread
    with app.app_context():
        try:
            # Update task status to running
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
    # Register a new task in the database
    task_id = register_task(
        file_key=file_key,
        filename=filename,
        deck_id=deck_id,
        deck_name=deck_name,
        user_id=user_id
    )
    
    # Start processing the first chunk
    thread = threading.Thread(
        target=process_chunk,
        args=(task_id, app, gemini_client, file_key, 0)
    )
    thread.daemon = True
    thread.start()
    
    return task_id
