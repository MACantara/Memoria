iimport os
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('POSTGRES_URL_NON_POOLING', '').replace('postgres://', 'postgresql://')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API Keys
    GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")

    # Development settings
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # Flashcard import and generation settings
    ALLOWED_EXTENSIONS = {'txt', 'pdf'}
    DEFAULT_BATCH_SIZE = 100  # Number of cards to generate per request
    CHUNK_SIZE = 15000        # Maximum number of characters per chunk
    
    # JSON Schema for multiple-choice flashcards
    FLASHCARD_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "q": {"type": "string"},  # short for question
                "ca": {"type": "string"}, # short for correct_answer
                "ia": {                   # short for incorrect_answers
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 3
                }
            },
            "required": ["q", "ca", "ia"]
        }
    }
    
    # Gemini API configuration
    GEMINI_CONFIG = {
        'response_mime_type': 'application/json',
        'response_schema': FLASHCARD_SCHEMA
    }
    
    GEMINI_MODEL = "gemini-2.0-flash-lite"
    
    @staticmethod
    def generate_prompt_template(topic, batch_size=None):
        """Generate a prompt template for AI flashcard generation"""
        if batch_size is None:
            batch_size = Config.DEFAULT_BATCH_SIZE
            
        return f"""
        <data>{topic}</data>
        <instructions>
        You are an expert educator creating flashcards about <data>.
        Generate comprehensive, accurate, and engaging flashcards following these strict guidelines:

        1. Each flashcard must have:
           - A clear, concise question that tests understanding
           - One definitively correct answer
           - Three plausible but incorrect answers
           - CRITICAL: All answers (correct and incorrect) MUST:
             * Be similar in length (within 10-15 characters of each other)
             * Use the same level of detail and complexity
             * Follow the same grammatical structure
             * Be equally specific/general
        
        2. Question types must be evenly distributed:
           - Factual recall (25% of cards)
           - Concept application (25% of cards)
           - Problem-solving (25% of cards)
           - Relationships between concepts (25% of cards)
        
        3. Ensure quality control:
           - No duplicate questions or answers
           - All content is factually accurate
           - Clear, unambiguous wording
           - Progressive difficulty (easy -> medium -> hard)
           - Avoid answers that are obviously wrong
           - Don't make the correct answer stand out by length or detail
        
        Format your response as a JSON array of objects, each with:
        - 'q': the flashcard question (short for question)
        - 'ca': the correct answer (short for correct_answer)
        - 'ia': array of exactly three incorrect answers (short for incorrect_answers)

        Generate {batch_size} unique flashcards covering different aspects of the topic.
        Ensure comprehensive coverage by:
        1. Breaking down the topic into key subtopics
        2. Creating equal numbers of cards for each subtopic
        3. Varying question types within each subtopic
        4. Including both fundamental and advanced concepts
        5. Maintaining consistent answer length and style throughout
        </instructions>
        """
