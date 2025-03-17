import os
import tempfile
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

class Config:
    # Secret key for session management
    SECRET_KEY = os.getenv('SECRET_KEY')
    
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
    
    # Use temporary directory for Vercel
    UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'flashcard_uploads')
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
    
    # Gemini API configuration - merged with FLASHCARD_CONFIG settings
    GEMINI_CONFIG = types.GenerateContentConfig(
        temperature=0.7,
        top_p=0.95,
        top_k=20,
        candidate_count=1,
        max_output_tokens=8192,
        response_mime_type="application/json",  # Ensure JSON response
        response_schema=FLASHCARD_SCHEMA,       # Include the schema
        stop_sequences=['###'],
        system_instruction=(
            "You are a professional educator creating multiple-choice flashcards. "
            "Each flashcard must have a question, one correct answer, and three incorrect answers. "
            "Your responses must strictly follow the JSON schema provided."
        )
    )
    
    GEMINI_MODEL = "gemini-2.0-flash-lite"
    
       
    # Learning-specific Gemini configuration with different settings for educational content
    LEARNING_GEMINI_CONFIG = {
        "temperature": 0.2,  # Lower temperature for more focused and predictable educational content
        "top_p": 0.8,        # Slightly higher top_p to allow some creativity in explanations
        "top_k": 40,         # Standard top_k
        "max_output_tokens": 2048,  # Allow longer responses for educational content
        "response_mime_type": "text/plain"
    }

    # Question-specific configuration for more structured JSON outputs
    QUESTION_GEMINI_CONFIG = {
        "temperature": 0.1,  # Very low temperature for consistent question format
        "top_p": 0.7,
        "top_k": 30,
        "max_output_tokens": 1024,
        "response_mime_type": "application/json",
        "response_schema": FLASHCARD_SCHEMA,
        "stop_sequences": ["###"],
        "system_instruction": (
            "You are a professional educator creating multiple-choice flashcards. "
            "Each flashcard must have a question, one correct answer, and three incorrect answers. "
            "Your responses must strictly follow the JSON schema provided."
        )
    }
    
    # Learning prompts 
    LEARNING_OUTLINE_PROMPT = """
        Create a structured learning outline for: {topic}
        
        Please provide a concise outline with 4-6 focused sections that would help someone learn this topic efficiently.
        Each section should be specific and focused on one aspect.
        
        Format your response as a JSON array of section titles as simple strings and not numbered, like this example:
        ["Introduction to {topic}", "Key Concepts", ...]
        
        Important requirements:
        - Make sections focused on one aspect each
        - Use clear, straightforward language
        - Keep titles concise (under 8 words)
        - Arrange sections in a logical learning progression
        - Do NOT return complex data structures, only string titles
        
        Only return the JSON array of section title strings, nothing else.
    """
    
    LEARNING_CONTENT_PROMPT = """
        I'm learning about: {topic}
        
        Create concise, focused learning content for this specific section:
        "{section_title}"
        
        Requirements:
        1. Keep content brief but substantive (approximately 250-350 words)
        2. Focus on core concepts and essential knowledge
        3. Use simple language and explain technical terms
        4. Include 1-2 clear examples or applications
        5. Use bullet points or short paragraphs for readability
        6. Format with HTML for structure (use h3, p, ul, li tags)
        
        The goal is to help me understand this topic without overwhelming me with too much information.
    """
    
    LEARNING_QUESTIONS_PROMPT = """
        Based on this educational content about "{topic}" on "{section_title}":
        
        {section_content}
        
        Generate {num_questions} focused multiple-choice questions that test understanding of the key concepts.
        
        Requirements:
        1. Each question should test ONE important concept from the content
        2. Questions should be clear and direct (avoid complex scenarios)
        3. The correct answer must be unambiguously supported by the content
        4. Provide 3 plausible but clearly incorrect alternatives
        5. Format your response as a JSON array of question objects:
        [{{
            "question": "What is X?",
            "correct_answer": "The correct answer",
            "incorrect_answers": ["Wrong 1", "Wrong 2", "Wrong 3"]
        }}]
        
        Only return the JSON array, nothing else.
    """
    
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
