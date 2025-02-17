import sys
from pathlib import Path
import json
from datetime import datetime
from sqlalchemy import text

# Add parent directory to path so we can import our app modules
sys.path.append(str(Path(__file__).parent.parent))

from app import app, db
from models import FlashcardDecks, Flashcards

def migrate_database():
    """Migrate data from old schema (Topic, Deck, Flashcard) to new schema (FlashcardDecks, Flashcards)"""
    with app.app_context():
        try:
            print("Starting migration process...")
            
            # Create new tables first
            print("\nCreating new schema tables...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS flashcard_decks (
                    flashcard_deck_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parent_deck_id INTEGER REFERENCES flashcard_decks(flashcard_deck_id)
                )
            """))
            
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS flashcards (
                    flashcard_id SERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    incorrect_answers JSON NOT NULL,
                    flashcard_deck_id INTEGER REFERENCES flashcard_decks(flashcard_deck_id) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_reviewed TIMESTAMP,
                    correct_count INTEGER DEFAULT 0,
                    incorrect_count INTEGER DEFAULT 0
                )
            """))
            
            db.session.commit()
            
            # Get data from old tables
            print("\nFetching data from old tables...")
            old_topics = db.session.execute(
                text("SELECT id, name, created_at FROM topics")
            ).fetchall()
            
            old_decks = db.session.execute(
                text("SELECT id, name, description, topic_id, created_at FROM decks")
            ).fetchall()
            
            old_flashcards = db.session.execute(
                text("""
                    SELECT id, question, correct_answer, incorrect_answers, 
                           deck_id, created_at, last_reviewed, 
                           correct_count, incorrect_count 
                    FROM flashcard
                """)
            ).fetchall()
            
            print(f"Found {len(old_topics)} topics, {len(old_decks)} decks, and {len(old_flashcards)} flashcards")
            
            # Create backup before making changes
            backup_old_data(old_topics, old_decks, old_flashcards)
            
            # Clear any existing data in new tables
            print("\nClearing existing data in new tables...")
            db.session.execute(text("TRUNCATE TABLE flashcards CASCADE"))
            db.session.execute(text("TRUNCATE TABLE flashcard_decks CASCADE"))
            db.session.commit()
            
            # Maps for tracking relationships
            topic_deck_map = {}
            deck_map = {}
            
            # Create main decks from topics
            print("\nCreating main decks...")
            for topic in old_topics:
                new_deck = FlashcardDecks(
                    name=topic.name,
                    description=f"Migrated from topic: {topic.name}",
                    created_at=topic.created_at,
                    parent_deck_id=None
                )
                db.session.add(new_deck)
                db.session.flush()
                topic_deck_map[topic.id] = new_deck.flashcard_deck_id
            
            db.session.commit()
            
            # Create sub-decks
            print("\nCreating sub-decks...")
            for deck in old_decks:
                parent_deck_id = topic_deck_map.get(deck.topic_id)
                new_deck = FlashcardDecks(
                    name=deck.name,
                    description=deck.description,
                    created_at=deck.created_at,
                    parent_deck_id=parent_deck_id
                )
                db.session.add(new_deck)
                db.session.flush()
                deck_map[deck.id] = new_deck.flashcard_deck_id
            
            db.session.commit()
            
            # Migrate flashcards
            print("\nMigrating flashcards...")
            cards_added = 0
            for card in old_flashcards:
                new_deck_id = deck_map.get(card.deck_id)
                if new_deck_id:
                    new_card = Flashcards(
                        question=card.question,
                        correct_answer=card.correct_answer,
                        incorrect_answers=card.incorrect_answers,
                        flashcard_deck_id=new_deck_id,
                        created_at=card.created_at,
                        last_reviewed=card.last_reviewed,
                        correct_count=card.correct_count,
                        incorrect_count=card.incorrect_count
                    )
                    db.session.add(new_card)
                    cards_added += 1
                    if cards_added % 100 == 0:
                        print(f"Migrated {cards_added} flashcards...")
            
            db.session.commit()
            
            # Drop old tables in correct order with CASCADE
            print("\nDropping old tables...")
            db.session.execute(text("DROP TABLE IF EXISTS flashcard CASCADE"))  # Drop child table first
            db.session.execute(text("DROP TABLE IF EXISTS decks CASCADE"))
            db.session.execute(text("DROP TABLE IF EXISTS topics CASCADE"))
            db.session.commit()
            
            print("\nMigration completed successfully!")
            print(f"Created {len(topic_deck_map)} main decks")
            print(f"Created {len(deck_map)} sub-decks")
            print(f"Migrated {cards_added} flashcards")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {e}")
            raise

def backup_old_data(topics, decks, flashcards):
    """Create a backup of old data before dropping tables"""
    backup_dir = Path(__file__).parent.parent / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'pre_migration_backup_{timestamp}.json'
    
    def row_to_dict(row):
        # Convert SQLAlchemy Row to dict using _mapping attribute
        return dict(row._mapping)
    
    # Convert all rows to dictionaries
    backup_data = {
        'topics': [row_to_dict(t) for t in topics],
        'decks': [row_to_dict(d) for d in decks],
        'flashcards': [row_to_dict(f) for f in flashcards]
    }
    
    # Convert datetime objects to strings
    def serialize_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, default=serialize_datetime, indent=2)
    
    print(f"\nBackup created: {backup_file}")

if __name__ == '__main__':
    if input("This will migrate data to the new schema. Are you sure? (y/N) ").lower() != 'y':
        print("Migration cancelled")
        sys.exit(0)
    
    migrate_database()
