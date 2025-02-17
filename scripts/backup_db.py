import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import our app modules
sys.path.append(str(Path(__file__).parent.parent))

from app import app, db
from models import Topic, Deck, Flashcard

def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def create_backup():
    backup_dir = Path(__file__).parent.parent / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'memoria_backup_{timestamp}.json'
    
    with app.app_context():
        # Get all topics with their relationships
        topics = Topic.query.all()
        
        backup_data = {
            'topics': [],
            'decks': [],
            'flashcards': []
        }
        
        # Serialize topics
        for topic in topics:
            backup_data['topics'].append({
                'id': topic.id,
                'name': topic.name,
                'created_at': topic.created_at
            })
            
            # Serialize decks for this topic
            for deck in topic.decks:
                backup_data['decks'].append({
                    'id': deck.id,
                    'name': deck.name,
                    'description': deck.description,
                    'topic_id': deck.topic_id,
                    'created_at': deck.created_at
                })
                
                # Serialize flashcards for this deck
                for card in deck.flashcards:
                    backup_data['flashcards'].append({
                        'id': card.id,
                        'question': card.question,
                        'correct_answer': card.correct_answer,
                        'incorrect_answers': card.incorrect_answers,
                        'topic_id': card.topic_id,
                        'deck_id': card.deck_id,
                        'created_at': card.created_at,
                        'last_reviewed': card.last_reviewed,
                        'correct_count': card.correct_count,
                        'incorrect_count': card.incorrect_count
                    })
        
        # Write backup to file
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, default=serialize_datetime, indent=2, ensure_ascii=False)
        
        print(f"Backup created successfully: {backup_file}")
        print(f"Backed up {len(backup_data['topics'])} topics, "
              f"{len(backup_data['decks'])} decks, and "
              f"{len(backup_data['flashcards'])} flashcards")

if __name__ == '__main__':
    try:
        create_backup()
    except Exception as e:
        print(f"Error creating backup: {e}")
        sys.exit(1)
