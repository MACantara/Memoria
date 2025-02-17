import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import our app modules
sys.path.append(str(Path(__file__).parent.parent))

from app import app, db
from models import db, FlashcardDecks, Flashcards

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
        print("Clearing existing data...")
        Flashcards.query.delete()
        FlashcardDecks.query.delete()
        db.session.commit()
        
        # First restore all decks without parent relationships
        print("\nRestoring decks...")
        for deck_data in backup_data['decks']:
            deck = FlashcardDecks(
                flashcard_deck_id=deck_data['flashcard_deck_id'],
                name=deck_data['name'],
                description=deck_data['description'],
                parent_deck_id=deck_data['parent_deck_id'],
                created_at=parse_datetime(deck_data['created_at'])
            )
            db.session.add(deck)
        
        # Commit decks to ensure all IDs are available for flashcards
        db.session.commit()
        
        # Now restore flashcards
        print("Restoring flashcards...")
        for card_data in backup_data['flashcards']:
            card = Flashcards(
                flashcard_id=card_data['flashcard_id'],
                question=card_data['question'],
                correct_answer=card_data['correct_answer'],
                incorrect_answers=card_data['incorrect_answers'],
                flashcard_deck_id=card_data['flashcard_deck_id'],
                created_at=parse_datetime(card_data['created_at']),
                last_reviewed=parse_datetime(card_data['last_reviewed']),
                correct_count=card_data['correct_count'],
                incorrect_count=card_data['incorrect_count']
            )
            db.session.add(card)
        
        db.session.commit()
        print(f"\nRestore completed successfully!")
        print(f"Restored {len(backup_data['decks'])} decks and "
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
