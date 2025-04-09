import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .base_screen import BaseScreen
from models import FlashcardDecks, Flashcards
import json
import os
import traceback
from datetime import datetime
from google import genai
import threading
from dotenv import load_dotenv

load_dotenv()

class ImportScreen(BaseScreen):
    """Screen for importing flashcards"""
    
    def setup_ui(self):
        # Create main container
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Import Flashcards", font=("TkDefaultFont", 16))
        title_label.pack(pady=(0, 20))
        
        # Tabs for different import methods
        self.tab_control = ttk.Notebook(main_frame)
        
        # File import tab
        file_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(file_tab, text="Import from File")
        
        # Text import tab
        text_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(text_tab, text="Import from Text")
        
        self.tab_control.pack(expand=True, fill=tk.BOTH)
        
        # Setup file import tab
        self.setup_file_import(file_tab)
        
        # Setup text import tab
        self.setup_text_import(text_tab)
        
        # Back button
        back_btn = ttk.Button(main_frame, text="Back to Decks", command=self.ui_manager.show_decks)
        back_btn.pack(side=tk.LEFT, pady=(10, 0))
        
    def setup_file_import(self, parent):
        # File selection frame
        file_frame = ttk.LabelFrame(parent, text="Select File")
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # File path entry and browse button
        file_path_frame = ttk.Frame(file_frame)
        file_path_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.file_path_var = tk.StringVar()
        file_path_entry = ttk.Entry(file_path_frame, textvariable=self.file_path_var, width=50)
        file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = ttk.Button(file_path_frame, text="Browse...", command=self.browse_file)
        browse_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Import options
        options_frame = ttk.LabelFrame(parent, text="Import Options")
        options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Deck selection
        deck_frame = ttk.Frame(options_frame)
        deck_frame.pack(fill=tk.X, padx=10, pady=5)
        
        deck_label = ttk.Label(deck_frame, text="Import to Deck:")
        deck_label.pack(side=tk.LEFT)
        
        self.deck_var = tk.StringVar()
        self.deck_combo = ttk.Combobox(deck_frame, textvariable=self.deck_var, state="readonly", width=40)
        self.deck_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # New deck option
        new_deck_frame = ttk.Frame(options_frame)
        new_deck_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.new_deck_var = tk.BooleanVar(value=False)
        new_deck_check = ttk.Checkbutton(new_deck_frame, text="Create New Deck", 
                                       variable=self.new_deck_var,
                                       command=self.toggle_new_deck)
        new_deck_check.pack(side=tk.LEFT)
        
        # New deck name entry (initially disabled)
        self.new_deck_name_var = tk.StringVar()
        self.new_deck_entry = ttk.Entry(new_deck_frame, textvariable=self.new_deck_name_var, 
                                     width=40, state=tk.DISABLED)
        self.new_deck_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Import button
        import_btn = ttk.Button(parent, text="Import File", command=self.import_file)
        import_btn.pack(pady=10)
        
        # Status area
        self.file_status_var = tk.StringVar()
        status_label = ttk.Label(parent, textvariable=self.file_status_var)
        status_label.pack(padx=10, pady=10)
    
    def setup_text_import(self, parent):
        # Instructions
        instructions = ttk.Label(parent, text="Paste text content to import. Each line should contain a question and answer separated by '::' or a tab.")
        instructions.pack(padx=10, pady=10, fill=tk.X)
        
        # Text area
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_area = tk.Text(text_frame, height=10, width=50)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=self.text_area.yview)
        self.text_area.config(yscrollcommand=scrollbar.set)
        
        # Import options
        options_frame = ttk.LabelFrame(parent, text="Import Options")
        options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Deck selection
        deck_frame = ttk.Frame(options_frame)
        deck_frame.pack(fill=tk.X, padx=10, pady=5)
        
        deck_label = ttk.Label(deck_frame, text="Import to Deck:")
        deck_label.pack(side=tk.LEFT)
        
        self.text_deck_var = tk.StringVar()
        self.text_deck_combo = ttk.Combobox(deck_frame, textvariable=self.text_deck_var, state="readonly", width=40)
        self.text_deck_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # New deck option
        new_text_deck_frame = ttk.Frame(options_frame)
        new_text_deck_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.new_text_deck_var = tk.BooleanVar(value=False)
        new_text_deck_check = ttk.Checkbutton(new_text_deck_frame, text="Create New Deck", 
                                          variable=self.new_text_deck_var,
                                          command=self.toggle_new_text_deck)
        new_text_deck_check.pack(side=tk.LEFT)
        
        # New deck name entry (initially disabled)
        self.new_text_deck_name_var = tk.StringVar()
        self.new_text_deck_entry = ttk.Entry(new_text_deck_frame, textvariable=self.new_text_deck_name_var, 
                                        width=40, state=tk.DISABLED)
        self.new_text_deck_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Import button
        import_text_btn = ttk.Button(parent, text="Import Text", command=self.import_text)
        import_text_btn.pack(pady=10)
        
        # Status area
        self.text_status_var = tk.StringVar()
        text_status_label = ttk.Label(parent, textvariable=self.text_status_var)
        text_status_label.pack(padx=10, pady=10)
    
    def refresh(self):
        """Load available decks and refresh UI"""
        # Load available decks for both tabs
        decks = self.db_session.query(FlashcardDecks).all()
        
        # Use the correct primary key attribute name
        deck_options = [(deck.flashcard_deck_id, deck.name) for deck in decks]
        
        # Update file tab combobox
        self.deck_combo['values'] = [name for _, name in deck_options]
        self.file_deck_ids = [id for id, _ in deck_options]
        
        # Update text tab combobox
        self.text_deck_combo['values'] = [name for _, name in deck_options]
        self.text_deck_ids = [id for id, _ in deck_options]
        
        # Reset status
        self.file_status_var.set("")
        self.text_status_var.set("")
        
        # Initialize API key if not already done
        if not hasattr(self, 'api_key'):
            self.api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
            if not self.api_key:
                messagebox.showwarning("API Key Missing", 
                                    "Google Gemini API key not found. AI-powered import will not work.")
    
    def browse_file(self):
        """Open file dialog to select a file"""
        filetypes = (
            ('Text files', '*.txt'),
            ('All files', '*.*')
        )
        
        filename = filedialog.askopenfilename(
            title="Select a file",
            initialdir=".",
            filetypes=filetypes
        )
        
        if filename:
            self.file_path_var.set(filename)
    
    def toggle_new_deck(self):
        """Toggle new deck entry field"""
        if self.new_deck_var.get():
            self.new_deck_entry.config(state=tk.NORMAL)
            self.deck_combo.config(state=tk.DISABLED)
        else:
            self.new_deck_entry.config(state=tk.DISABLED)
            self.deck_combo.config(state="readonly")
    
    def toggle_new_text_deck(self):
        """Toggle new deck entry field for text import"""
        if self.new_text_deck_var.get():
            self.new_text_deck_entry.config(state=tk.NORMAL)
            self.text_deck_combo.config(state=tk.DISABLED)
        else:
            self.new_text_deck_entry.config(state=tk.DISABLED)
            self.text_deck_combo.config(state="readonly")
    
    def _get_target_deck(self, new_deck_var, new_deck_name_var, deck_combo, deck_ids):
        """Helper to get or create target deck"""
        if new_deck_var.get():
            # Create new deck
            deck_name = new_deck_name_var.get().strip()
            if not deck_name:
                messagebox.showerror("Error", "Please enter a name for the new deck")
                return None
                
            try:
                new_deck = FlashcardDecks(
                    name=deck_name,
                    description=f"Imported {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                self.db_session.add(new_deck)
                self.db_session.flush()  # Get ID without committing
                # Use correct attribute name
                return new_deck.flashcard_deck_id
            except Exception as e:
                self.db_session.rollback()
                messagebox.showerror("Error", f"Failed to create deck: {str(e)}")
                return None
        else:
            # Use existing deck
            selected_index = deck_combo.current()
            if selected_index < 0:
                messagebox.showerror("Error", "Please select a deck")
                return None
                
            return deck_ids[selected_index]
    
    def _parse_content(self, content):
        """Parse content into flashcards"""
        flashcards = []
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
                
            # Try different separators
            if '::' in line:
                parts = line.split('::', 1)
            elif '\t' in line:
                parts = line.split('\t', 1)
            else:
                continue
                
            if len(parts) == 2:
                front = parts[0].strip()
                back = parts[1].strip()
                if front and back:
                    flashcards.append((front, back))
                    
        return flashcards
    
    def import_file(self):
        """Import flashcards from file using Gemini AI"""
        file_path = self.file_path_var.get()
        
        if not file_path:
            messagebox.showerror("Error", "Please select a file to import")
            return
            
        # Check if the file type is allowed (only txt for now)
        allowed_extensions = {'txt'}
        if not '.' in file_path or file_path.rsplit('.', 1)[1].lower() not in allowed_extensions:
            messagebox.showerror("Error", "File type not allowed. Only TXT files are supported.")
            return
        
        try:
            # Get or create deck
            deck_id = self._get_target_deck(self.new_deck_var, self.new_deck_name_var,
                                       self.deck_combo, self.file_deck_ids)
            
            if deck_id is None:
                return
                
            # Read the text content
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                file_text = f.read()
                
            # Check if we have enough text to process
            if len(file_text) < 100:
                messagebox.showerror("Error", "Not enough text in the file. Please provide a file with more content.")
                return
                
            # Update status
            self.file_status_var.set("Processing... This may take a minute.")
            self.frame.update()  # Force UI update
            
            # Use threading to avoid freezing the UI
            threading.Thread(
                target=self._process_with_ai,
                args=(file_text, deck_id, os.path.basename(file_path), "file"),
                daemon=True
            ).start()
                
        except Exception as e:
            self.db_session.rollback()
            self.file_status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Import Error", str(e))
    
    def import_text(self):
        """Import flashcards from pasted text using Gemini AI"""
        content = self.text_area.get(1.0, tk.END)
        
        if not content.strip() or len(content.strip()) < 50:
            messagebox.showerror("Error", "Text content is too short. Please provide more content.")
            return
        
        try:
            # Get or create deck
            deck_id = self._get_target_deck(self.new_text_deck_var, self.new_text_deck_name_var,
                                       self.text_deck_combo, self.text_deck_ids)
            
            if deck_id is None:
                return
                
            # Update status
            self.text_status_var.set("Processing... This may take a minute.")
            self.frame.update()  # Force UI update
            
            # Use threading to avoid freezing the UI
            threading.Thread(
                target=self._process_with_ai,
                args=(content, deck_id, "Pasted Text", "text"),
                daemon=True
            ).start()
                
        except Exception as e:
            self.db_session.rollback()
            self.text_status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Import Error", str(e))
    
    def _process_with_ai(self, content, deck_id, content_name, source_type):
        """Process content with Gemini AI and create flashcards"""
        try:
            # Check if API key is available
            if not self.api_key:
                raise ValueError("Google Gemini API key is not configured")
                
            # Initialize the API client
            client = genai.Client(api_key=self.api_key)
            
            # Generate prompt template
            deck = self.db_session.query(FlashcardDecks).filter_by(flashcard_deck_id=deck_id).first()
            prompt = self._generate_prompt_template(f"content: {deck.name}", 100)
            
            # Truncate content if it's too long
            content_for_api = content[:4000] + "..." if len(content) > 4000 else content
            
            # Use schema with shorter field names for optimization
            schema = {
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
            
            # Send request to Gemini
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=f"{prompt}\n\nContent:\n{content_for_api}",
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': schema
                }
            )
            
            # Try to parse the response as JSON
            try:
                flashcards_data = json.loads(response.text)
            except json.JSONDecodeError:
                # Fallback to manual parsing
                flashcards_data = self._parse_flashcards(response.text)
            
            if not flashcards_data:
                raise ValueError("No flashcards could be generated from this content")
            
            # Save to database
            now = datetime.now()
            cards_added = 0
            
            for card in flashcards_data:
                if hasattr(card, 'model_dump'):
                    card = card.model_dump()
                    
                # Use the abbreviated field names (with fallback to old names)
                question = card.get('q', card.get('question', ''))
                correct_answer = card.get('ca', card.get('correct_answer', ''))
                incorrect_answers = card.get('ia', card.get('incorrect_answers', []))[:3]
                
                # Pad with empty answers if needed
                while len(incorrect_answers) < 3:
                    incorrect_answers.append(f"Incorrect answer {len(incorrect_answers) + 1}")
                
                flashcard = Flashcards(
                    question=question,
                    correct_answer=correct_answer,
                    incorrect_answers=json.dumps(incorrect_answers),
                    flashcard_deck_id=deck_id,
                    created_at=now,
                    state=0  # Explicitly set to NEW_STATE
                )
                
                # Initialize FSRS state if available
                if hasattr(flashcard, 'init_fsrs_state'):
                    flashcard.init_fsrs_state()
                
                self.db_session.add(flashcard)
                cards_added += 1
            
            self.db_session.commit()
            
            # Update UI on the main thread
            if source_type == "file":
                self.frame.after(0, lambda: self.file_status_var.set(
                    f"Successfully generated {cards_added} flashcards"))
            else:
                self.frame.after(0, lambda: self.text_status_var.set(
                    f"Successfully generated {cards_added} flashcards"))
                
        except Exception as e:
            # Clean up and show error
            self.db_session.rollback()
            
            error_message = f"Error: {str(e)}"
            if source_type == "file":
                self.frame.after(0, lambda: self.file_status_var.set(error_message))
            else:
                self.frame.after(0, lambda: self.text_status_var.set(error_message))
                
            print(f"Import error: {str(e)}")
            print(traceback.format_exc())
    
    def _generate_prompt_template(self, topic, batch_size):
        """Generate a prompt template for AI flashcard generation"""
        return f"""You are an expert educator creating flashcards about {topic}.
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
        5. Maintaining consistent answer length and style throughout"""

    def _parse_flashcards(self, text):
        """Fallback parser for when structured output fails"""
        lines = text.split('\n')
        cards = []
        current_card = None
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
                
            # Look for patterns that might indicate JSON structure
            if line.startswith('{') and '"q"' in line:
                try:
                    # Try to parse a single JSON object
                    card = json.loads(line)
                    if 'q' in card and 'ca' in card:
                        cards.append(card)
                        continue
                except:
                    pass
            
            # Look for numbered items like "1. Question: What is..."
            if (line[0].isdigit() and line[1] in ['.', ')']) or line.lower().startswith('question:'):
                if current_card:
                    cards.append(current_card)
                
                question = line.split(':', 1)[1].strip() if ':' in line else line
                current_card = {
                    'q': question,
                    'ca': '',
                    'ia': []
                }
            elif current_card and (line.lower().startswith('answer:') or line.lower().startswith('correct:')):
                current_card['ca'] = line.split(':', 1)[1].strip() if ':' in line else line
            elif current_card and line.lower().startswith('incorrect:'):
                current_card['ia'].append(line.split(':', 1)[1].strip() if ':' in line else line)
        
        # Add the last card if it exists
        if current_card and current_card['q'] and current_card['ca']:
            cards.append(current_card)
                
        return cards