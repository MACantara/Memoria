# Memoria - AI-Enhanced Learning Platform

Memoria is an intelligent learning platform that leverages AI to help users create, organize, and study flashcards with optimized spaced repetition. The application combines proven learning techniques with modern AI capabilities to enhance knowledge retention and study efficiency.

## 🌟 Features

- **AI-Powered Flashcard Generation**: Import content from various sources (TXT, PDF) and automatically generate high-quality flashcards using Google's Gemini AI
- **Organized Learning Structure**: Create hierarchical deck structures to organize study materials
- **Spaced Repetition System**: Uses the FSRS (Free Spaced Repetition Scheduler) algorithm for optimal review scheduling
- **Guided Learning Paths**: Create structured learning paths with sections and progression
- **Comprehensive Statistics**: Track learning progress with detailed analytics
- **Database Synchronization**: Seamlessly sync between SQLite (local) and PostgreSQL (cloud) databases
- **Responsive Design**: Works on desktop and mobile devices

## 🔧 Installation

### Prerequisites

- Python 3.9+
- pip (Python package manager)
- Git

### Step-by-Step Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/memoria.git
   cd memoria
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables by copying the example:
   ```bash
   cp example.env .env
   ```
   Then edit `.env` with your specific configuration values.

5. Initialize the database:
   ```bash
   python cli.py init-db
   ```

6. Run the application:
   ```bash
   python app.py
   ```

7. Access the application at: `http://localhost:5000`

## 🗄️ Database Configuration

Memoria supports both SQLite (for local development) and PostgreSQL (for production/cloud deployment). The database configuration is managed through environment variables in the .env file:

```
# Database configuration
DB_TYPE=sqlite             # 'sqlite' or 'postgres'
SQLITE_DB_PATH=data/memoria.db
```

### Database Synchronization

The application includes functionality to synchronize data between SQLite and PostgreSQL databases, enabling offline work that can be later synchronized with a cloud database:

```
# Synchronize databases (both directions)
python cli.py db-sync

# Synchronize from Postgres to SQLite only
python cli.py db-sync --direction postgres_to_sqlite

# Synchronize specific tables
python cli.py db-sync --tables users flashcard_decks
```

## 🤖 AI Integration

Memoria uses Google's Gemini API to generate flashcards and learning content. To use these features, you need to:

1. Get a Gemini API key from Google AI Studio
2. Add it to your `.env` file:

```
GOOGLE_GEMINI_API_KEY="your-api-key"
```

The application includes specialized prompts for different educational tasks:
- Flashcard generation
- Learning path outline creation
- Educational content generation
- Assessment question creation

## Key Components

- Flask: Web framework
- SQLAlchemy: Database ORM
- Google Gemini: AI content generation
- Bootstrap: Frontend styling
- Chart.js: Statistics visualization

## Contributing

The project is currently not accepting any contributions. This may change in the future.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.