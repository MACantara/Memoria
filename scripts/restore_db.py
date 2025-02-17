import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import our app modules
sys.path.append(str(Path(__file__).parent.parent))

from app import app, db
from models import Topic, Deck, Flashcard

def parse_datetime(datetime_str):
    if datetime_str:
        return datetime.fromisoformat(datetime_str)
    return None

def restore_backup(backup_file):
    with app.app_context():
        # Read backup file
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        # Clear existing data
        Flashcard.query.delete()
        Deck.query.delete()
        Topic.query.delete()
        db.session.commit()
        
        # Restore topics
        for topic_data in backup_data['topics']:
            topic = Topic(
                id=topic_data['id'],
                name=topic_data['name'],
                created_at=parse_datetime(topic_data['created_at'])
            )
            db.session.add(topic)
        
        # Restore decks
        for deck_data in backup_data['decks']:
            deck = Deck(
                id=deck_data['id'],
                name=deck_data['name'],
                description=deck_data['description'],
                topic_id=deck_data['topic_id'],
                created_at=parse_datetime(deck_data['created_at'])
            )
            db.session.add(deck)
        
        # Restore flashcards
        for card_data in backup_data['flashcards']:
            card = Flashcard(
                id=card_data['id'],
                question=card_data['question'],
                correct_answer=card_data['correct_answer'],
                incorrect_answers=card_data['incorrect_answers'],
                topic_id=card_data['topic_id'],
                deck_id=card_data['deck_id'],
                created_at=parse_datetime(card_data['created_at']),
                last_reviewed=parse_datetime(card_data['last_reviewed']),
                correct_count=card_data['correct_count'],
                incorrect_count=card_data['incorrect_count']
            )
            db.session.add(card)
        
        db.session.commit()
        print(f"Restored {len(backup_data['topics'])} topics, "
              f"{len(backup_data['decks'])} decks, and "
              f"{len(backup_data['flashcards'])} flashcards")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python restore_db.py <backup_file>")
        sys.exit(1)
        
    backup_file = sys.argv[1]
    if not Path(backup_file).exists():
        print(f"Backup file not found: {backup_file}")
        sys.exit(1)
        
    try:
        restore_backup(backup_file)
    except Exception as e:
        print(f"Error restoring backup: {e}")
        sys.exit(1)
