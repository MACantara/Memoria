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
    
    GEMINI_MODEL = "models/gemini-1.5-pro-latest"
    
       
    # Learning-specific Gemini configuration with different settings for educational content
    LEARNING_GEMINI_CONFIG = {
        "temperature": 0.2,        # Lower temperature for more focused, consistent outputs
        "top_p": 0.95,             # Slightly reduced for more focused text generation
        "top_k": 40,               # Standard setting for diverse yet relevant outputs
        "max_output_tokens": 2048, # Set reasonable limits to avoid excessive content
        "response_mime_type": "text/plain"  # Explicitly request plain text responses
    }

    # Question-specific configuration for more structured JSON outputs
    QUESTION_GEMINI_CONFIG = {
        "temperature": 0.1,        # Very low temperature for consistent, accurate questions
        "top_p": 0.9,              # More focused for questions
        "top_k": 30,               # More constrained for better question accuracy
        "max_output_tokens": 1024, # Adequate for questions
        "response_mime_type": "application/json"  # Explicitly request JSON responses
    }
    
    # Enhanced outline generation prompt with clear structure and examples
    LEARNING_OUTLINE_PROMPT = """
    # Task: Create a Learning Path Outline

    ## Context
    You are an expert curriculum designer with experience creating focused, effective learning paths. Your task is to create a structured outline for a student learning about: "{topic}"

    ## Instructions
    1. Create a logical progression of 4-6 focused sections that build on each other
    2. Each section should cover ONE specific aspect of the topic
    3. Start with foundational concepts and progress to more advanced ideas
    4. Use precise, descriptive titles that clearly indicate what will be covered
    5. Format your response ONLY as a JSON array of section titles

    ## Requirements
    - Section titles must be concise (under 8 words)
    - Use clear, straightforward language accessible to beginners
    - Do NOT include section numbers in the titles
    - Ensure logical progression of knowledge
    - Include basic concepts before advanced applications

    ## Output Format
    Return ONLY a JSON array of strings like this example:
    ["Introduction to Topic", "Core Principles", "Key Applications", "Advanced Techniques", "Future Directions"]

    No additional text, explanations or markdown formatting - ONLY the JSON array.
    """
    
    # Enhanced content generation prompt with structural guidance
    LEARNING_CONTENT_PROMPT = """
    # Task: Create Educational Content

    ## Context
    You are an experienced educator creating clear, concise content for a student learning about:
    Topic: "{topic}" 
    Current Section: "{section_title}"

    ## Content Requirements
    1. Create concise but thorough educational content (300-350 words)
    2. Focus exclusively on the specific section topic
    3. Structure with clear headings, short paragraphs, and occasional bullet points
    4. Include 1-2 specific examples or applications
    5. Define any technical terms when first introduced
    6. Use a clear, friendly teaching tone suitable for an interested beginner

    ## Structure
    - Start with a brief 1-2 sentence introduction to the section topic
    - Explain key concepts in logical order
    - Include examples or applications to illustrate concepts
    - End with a brief summary or connection to the broader topic

    ## Format Requirements
    - Use HTML for formatting (<h3>, <p>, <ul>, <li>, <strong>)
    - Use <h3> tags for subsection headings
    - Use <strong> for important terms or concepts
    - Use bullet points (<ul>/<li>) for lists or steps
    - Break content into 3-4 paragraphs maximum
    - Do not use complex HTML - stick to basic structural elements

    ## Tone & Style
    - Clear, direct, and educational
    - Conversational but informative
    - Avoid unnecessary jargon
    - Assume the reader is intelligent but new to this specific topic
    
    Provide only the educational content without additional commentary.
    """
    
    # Enhanced question generation prompt with guidelines for effective assessment
    LEARNING_QUESTIONS_PROMPT = """
    # Task: Create Assessment Questions

    ## Context
    You are an educational assessment expert designing multiple-choice questions to test understanding of:
    Topic: "{topic}"
    Section: "{section_title}"

    Based on this educational content:
    ```
    {section_content}
    ```

    ## Instructions
    1. Create exactly {num_questions} multiple-choice questions that test understanding of key concepts
    2. Each question should focus on ONE specific concept from the content
    3. The correct answer must be clearly supported by the provided content
    4. Create 3 plausible but unambiguously incorrect alternatives for each question

    ## Question Requirements
    - Questions should be clear, direct, and unambiguous
    - Focus on comprehension and application, not just recall
    - Ensure questions test understanding, not just memorization
    - Vary question styles (definition, application, example identification)
    - Avoid extremely similar or overlapping questions

    ## Answer Requirements
    - Correct answer must be clearly defensible from the content
    - Incorrect options must be plausible but clearly wrong
    - Avoid using absolute terms (always, never, all, none)
    - All answers should be roughly similar in length and style
    - Don't include obvious incorrect options

    ## Output Format
    Return ONLY a JSON array with this exact structure:
    [{{
        "question": "What is X?",
        "correct_answer": "The correct answer",
        "incorrect_answers": ["Wrong 1", "Wrong 2", "Wrong 3"]
    }}]
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
