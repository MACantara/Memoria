import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from .base_screen import BaseScreen
from models import FlashcardDecks, Flashcards
import os
import json
from datetime import datetime

class GenerationScreen(BaseScreen):
    """Screen for AI-generated flashcards"""
    
    def setup_ui(self):
        # Create main container
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Generate Flashcards with AI", 
                             font=("TkDefaultFont", 16))
        title_label.pack(pady=(0, 20))
        
        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="Generation Options")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Topic
        topic_frame = ttk.Frame(input_frame)
        topic_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        topic_label = ttk.Label(topic_frame, text="Topic:")
        topic_label.pack(side=tk.LEFT)
        
        self.topic_var = tk.StringVar()
        topic_entry = ttk.Entry(topic_frame, textvariable=self.topic_var, width=50)
        topic_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Deck selection
        deck_frame = ttk.Frame(input_frame)
        deck_frame.pack(fill=tk.X, padx=10, pady=5)
        
        deck_label = ttk.Label(deck_frame, text="Add to Deck:")
        deck_label.pack(side=tk.LEFT)
        
        self.deck_var = tk.StringVar()
        self.deck_combo = ttk.Combobox(deck_frame, textvariable=self.deck_var, 
                                     state="readonly", width=40)
        self.deck_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # New deck option
        new_deck_frame = ttk.Frame(input_frame)
        new_deck_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.new_deck_var = tk.BooleanVar(value=False)
        new_deck_check = ttk.Checkbutton(new_deck_frame, text="Create New Deck", 
                                       variable=self.new_deck_var,
                                       command=self.toggle_new_deck)
        new_deck_check.pack(side=tk.LEFT)
        
        # Number of cards to generate
        count_frame = ttk.Frame(input_frame)
        count_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        count_label = ttk.Label(count_frame, text="Number of Cards:")
        count_label.pack(side=tk.LEFT)
        
        self.count_var = tk.IntVar(value=10)
        count_spinbox = ttk.Spinbox(count_frame, from_=1, to=50, 
                                  textvariable=self.count_var, width=5)
        count_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Generate button
        generate_btn = ttk.Button(main_frame, text="Generate Flashcards", 
                               command=self.generate_flashcards)
        generate_btn.pack(pady=10)
        
        # Results area
        results_frame = ttk.LabelFrame(main_frame, text="Generation Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a scrolled text widget for results
        self.results_text = scrolledtext.ScrolledText(results_frame, height=15, width=70, 
                                                   wrap=tk.WORD, state=tk.DISABLED)
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status label
        self.status_var = tk.StringVar()
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(pady=5)
        
        # Back button
        back_btn = ttk.Button(main_frame, text="Back to Decks", 
                           command=self.ui_manager.show_decks)
        back_btn.pack(side=tk.LEFT, pady=(10, 0))
        
        # Initialize API key
        self.api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        if not self.api_key:
            self.status_var.set("Warning: API key not found. Generation may not work.")
    
    def refresh(self):
        """Load available decks and refresh UI"""
        # Load available decks
        decks = self.db_session.query(FlashcardDecks).all()
        deck_options = [(deck.id, deck.name) for deck in decks]
        
        # Update combobox
        self.deck_combo['values'] = [name for _, name in deck_options]
        self.deck_ids = [id for id, _ in deck_options]
        
        # Reset status and results
        self.status_var.set("")
        self.update_results("")
    
    def toggle_new_deck(self):
        """Toggle the deck selection dropdown based on new deck checkbox"""
        if self.new_deck_var.get():
            self.deck_combo.config(state=tk.DISABLED)
        else:
            self.deck_combo.config(state="readonly")
    
    def update_results(self, text):
        """Update the results text area"""
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, text)
        self.results_text.config(state=tk.DISABLED)
    
    def generate_prompt(self, topic, count):
        """Generate a prompt for the AI"""
        return (
            f"Generate {count} flashcards about {topic}. "
            f"Format each flashcard as 'Question::Answer', one per line. "
            f"Make these high-quality, educational flashcards suitable for studying {topic}. "
            f"Ensure questions are clear and answers are concise."
        )
    
    def parse_flashcards(self, text):
        """Parse AI response into flashcards"""
        cards = []
        for line in text.splitlines():
            line = line.strip()
            if not line or '::' not in line:
                continue
            
            try:
                question, answer = line.split('::', 1)
                question = question.strip()
                answer = answer.strip()
                
                # Skip empty cards
                if question and answer:
                    cards.append((question, answer))
            except Exception:
                continue
                
        return cards
    
    def get_target_deck_id(self):
        """Get or create the target deck ID"""
        if self.new_deck_var.get():
            # Create new deck using the topic as name
            topic = self.topic_var.get().strip()
            if not topic:
                messagebox.showerror("Error", "Please enter a topic for the new deck")
                return None
                
            try:
                new_deck = FlashcardDecks(
                    name=topic,
                    description=f"AI-generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parent_deck_id=None
                )
                self.db_session.add(new_deck)
                self.db_session.flush()
                return new_deck.id
            except Exception as e:
                self.db_session.rollback()
                messagebox.showerror("Error", f"Failed to create deck: {str(e)}")
                return None
        else:
            # Use existing deck
            selected_index = self.deck_combo.current()
            if selected_index < 0:
                messagebox.showerror("Error", "Please select a deck")
                return None
                
            return self.deck_ids[selected_index]
    
    def generate_flashcards(self):
        """Generate flashcards using AI"""
        # Get input values
        topic = self.topic_var.get().strip()
        count = self.count_var.get()
        
        if not topic:
            messagebox.showerror("Error", "Please enter a topic")
            return
        
        # Update UI
        self.status_var.set("Generating flashcards... Please wait.")
        self.update_results("Processing request...")
        self.frame.update()  # Force UI update
        
        # Get or create target deck
        deck_id = self.get_target_deck_id()
        if deck_id is None:
            self.status_var.set("Failed to get or create deck.")
            return
        
        try:
            # In a real application, this would call the Gemini API
            # For this demo, we'll generate some mock flashcards
            self.generate_mock_flashcards(topic, count, deck_id)
            
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            self.update_results(f"Failed to generate flashcards:\n{str(e)}")
    
    def generate_mock_flashcards(self, topic, count, deck_id):
        """Generate mock flashcards for demo purposes"""
        # Create some sample flashcards based on the topic
        sample_cards = [
            (f"What is {topic}?", f"A subject of study focusing on {topic}."),
            (f"Who is known for contributions to {topic}?", f"Many scholars have contributed to {topic}, including pioneers in the field."),
            (f"When did {topic} become a formalized field?", f"The study of {topic} was formalized in the recent centuries."),
            (f"What is a key principle in {topic}?", f"One key principle is the fundamental understanding of core concepts."),
            (f"How is {topic} applied in real life?", f"There are many practical applications of {topic} in various fields.")
        ]
        
        # For demo purposes, multiply the cards to reach the requested count
        all_cards = []
        while len(all_cards) < count:
            all_cards.extend(sample_cards[:min(count - len(all_cards), len(sample_cards))])
        
        # Display the generated cards
        result_text = "Generated Flashcards:\n\n"
        for i, (front, back) in enumerate(all_cards, 1):
            result_text += f"{i}. Front: {front}\n   Back: {back}\n\n"
            
        self.update_results(result_text)
        
        # Save to database
        now = datetime.now()
        for front, back in all_cards:
            card = Flashcards(
                front=front,
                back=back,
                deck_id=deck_id,
                created=now
            )
            self.db_session.add(card)
            
        self.db_session.commit()
        self.status_var.set(f"Successfully generated {len(all_cards)} flashcards")
        
        # Refresh deck list
        self.refresh()
