from models import db
from datetime import datetime

class ImportFile(db.Model):
    """Tracks files being imported and processed"""
    __tablename__ = 'import_files'
    
    id = db.Column(db.Integer, primary_key=True)
    file_key = db.Column(db.String(64), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('flashcard_decks.flashcard_deck_id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_chunks = db.Column(db.Integer, default=0)
    current_index = db.Column(db.Integer, default=0)
    is_complete = db.Column(db.Boolean, default=False)
    total_saved_cards = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chunks = db.relationship('ImportChunk', back_populates='import_file', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<ImportFile {self.file_key} ({self.current_index}/{self.total_chunks})>"
    
    @property
    def processed_chunks_count(self):
        return ImportChunk.query.filter_by(file_id=self.id, is_processed=True).count()

    @property
    def saved_chunks_count(self):
        return ImportChunk.query.filter_by(file_id=self.id, is_saved=True).count()
    
    @property
    def saved_chunks(self):
        return [chunk.index for chunk in ImportChunk.query.filter_by(file_id=self.id, is_saved=True).all()]


class ImportChunk(db.Model):
    """Stores individual chunks of imported content"""
    __tablename__ = 'import_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('import_files.id'), nullable=False)
    index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_processed = db.Column(db.Boolean, default=False)
    is_saved = db.Column(db.Boolean, default=False)
    cards_saved = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    import_file = db.relationship('ImportFile', back_populates='chunks')
    
    __table_args__ = (
        db.UniqueConstraint('file_id', 'index', name='uix_chunk_file_index'),
    )
    
    def __repr__(self):
        return f"<ImportChunk {self.id} (file: {self.file_id}, index: {self.index})>"


class ImportFlashcard(db.Model):
    """Temporary storage for generated flashcards during import process"""
    __tablename__ = 'import_flashcards'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('import_files.id'), nullable=False)
    chunk_id = db.Column(db.Integer, db.ForeignKey('import_chunks.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=False)
    incorrect_answers = db.Column(db.JSON, default=list)
    is_saved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add index to speed up queries
    __table_args__ = (
        db.Index('idx_import_flashcards_file', 'file_id'),
    )
    
    def __repr__(self):
        return f"<ImportFlashcard {self.id} (file: {self.file_id}, chunk: {self.chunk_id})>"


class ImportTask(db.Model):
    """Tracks background import tasks"""
    __tablename__ = 'import_tasks'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID as string
    file_key = db.Column(db.String(64), db.ForeignKey('import_files.file_key'))
    filename = db.Column(db.String(255), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('flashcard_decks.flashcard_deck_id'), nullable=False)
    deck_name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    progress = db.Column(db.Integer, default=0)
    total_chunks = db.Column(db.Integer, default=0)
    current_chunk = db.Column(db.Integer, default=0)
    total_cards = db.Column(db.Integer, default=0)
    saved_cards = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    error = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        """Convert task to dictionary for API responses"""
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error
        }
