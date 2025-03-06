import tkinter as tk
from tkinter import ttk, messagebox
from .base_screen import BaseScreen
from models import FlashcardDecks, Flashcards

class StudyScreen(BaseScreen):
    """Screen for studying flashcards"""
    
    def setup_ui(self):
        # Create main container
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Study Flashcards", font=("TkDefaultFont", 16))
        title_label.pack(pady=(0, 20))
        
        # Deck selection section
        deck_frame = ttk.LabelFrame(main_frame, text="Select Deck")
        deck_frame.pack(fill=tk.X, pady=10)
        
        # Create combobox for deck selection
        self.deck_var = tk.StringVar()
        self.deck_combo = ttk.Combobox(deck_frame, textvariable=self.deck_var, state="readonly")
        self.deck_combo.pack(fill=tk.X, padx=10, pady=10)
        self.deck_combo.bind("<<ComboboxSelected>>", self.on_deck_selected)
        
        # Study controls
        study_frame = ttk.Frame(main_frame)
        study_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Card display
        self.card_frame = ttk.LabelFrame(study_frame, text="Flashcard")
        self.card_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initial message
        self.message_label = ttk.Label(self.card_frame, text="Select a deck to begin studying",
                                    justify=tk.CENTER, font=("TkDefaultFont", 12))
        self.message_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Card content (initially hidden)
        self.front_text = tk.Text(self.card_frame, height=5, width=50)
        self.back_text = tk.Text(self.card_frame, height=5, width=50)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Navigation buttons (initially disabled)
        self.show_answer_btn = ttk.Button(button_frame, text="Show Answer", 
                                       command=self.show_answer, state=tk.DISABLED)
        self.show_answer_btn.pack(side=tk.LEFT, padx=5)
        
        self.easy_btn = ttk.Button(button_frame, text="Easy", 
                                command=lambda: self.grade_card(3), state=tk.DISABLED)
        self.easy_btn.pack(side=tk.RIGHT, padx=5)
        
        self.medium_btn = ttk.Button(button_frame, text="Medium", 
                                  command=lambda: self.grade_card(2), state=tk.DISABLED)
        self.medium_btn.pack(side=tk.RIGHT, padx=5)
        
        self.hard_btn = ttk.Button(button_frame, text="Hard", 
                               command=lambda: self.grade_card(1), state=tk.DISABLED)
        self.hard_btn.pack(side=tk.RIGHT, padx=5)
        
        # Back button
        back_btn = ttk.Button(main_frame, text="Back to Decks", command=self.ui_manager.show_decks)
        back_btn.pack(side=tk.LEFT, pady=(10, 0))
        
        # Study state
        self.current_card = None
        self.showing_answer = False
        self.cards_to_study = []
    
    def refresh(self):
        """Load deck data and refresh UI"""
        # Load available decks
        decks = self.db_session.query(FlashcardDecks).all()
        deck_options = [(deck.id, deck.name) for deck in decks]
        
        # Update combobox
        self.deck_combo['values'] = [name for _, name in deck_options]
        self.deck_ids = [id for id, _ in deck_options]
        
        if not decks:
            self.message_label.config(text="No decks available. Create a deck first.")
    
    def on_deck_selected(self, event=None):
        """Handle deck selection"""
        selected_index = self.deck_combo.current()
        if selected_index >= 0:
            deck_id = self.deck_ids[selected_index]
            self.load_cards_for_study(deck_id)
    
    def load_cards_for_study(self, deck_id):
        """Load cards for the selected deck"""
        # For simplicity, just load all cards in the deck
        # In a real app, you would load cards due for review
        cards = self.db_session.query(Flashcards).filter_by(deck_id=deck_id).all()
        
        if not cards:
            self.message_label.config(text="No flashcards in this deck. Add some cards first.")
            self.reset_ui()
            return
            
        self.cards_to_study = cards
        self.start_study_session()
    
    def start_study_session(self):
        """Start a study session with the loaded cards"""
        if not self.cards_to_study:
            return
            
        # Hide message label and show card content
        self.message_label.pack_forget()
        self.front_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Enable navigation
        self.show_answer_btn.config(state=tk.NORMAL)
        
        # Show first card
        self.current_card = self.cards_to_study[0]
        self.showing_answer = False
        self.front_text.config(state=tk.NORMAL)
        self.front_text.delete(1.0, tk.END)
        self.front_text.insert(tk.END, self.current_card.front)
        self.front_text.config(state=tk.DISABLED)
    
    def show_answer(self):
        """Show the answer for the current card"""
        if not self.current_card:
            return
            
        # Show back of card
        if not self.showing_answer:
            self.back_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            self.back_text.config(state=tk.NORMAL)
            self.back_text.delete(1.0, tk.END)
            self.back_text.insert(tk.END, self.current_card.back)
            self.back_text.config(state=tk.DISABLED)
            
            # Hide show answer button, show grading buttons
            self.show_answer_btn.config(state=tk.DISABLED)
            self.easy_btn.config(state=tk.NORMAL)
            self.medium_btn.config(state=tk.NORMAL)
            self.hard_btn.config(state=tk.NORMAL)
            
            self.showing_answer = True
    
    def grade_card(self, grade):
        """Handle grading of the current card"""
        if not self.current_card:
            return
            
        # In a full implementation, this would update the card's scheduling
        # using spaced repetition algorithm (like FSRS)
        
        # Remove the current card from the study list
        self.cards_to_study.remove(self.current_card)
        
        if self.cards_to_study:
            # Show next card
            self.back_text.pack_forget()
            self.showing_answer = False
            
            # Reset buttons
            self.show_answer_btn.config(state=tk.NORMAL)
            self.easy_btn.config(state=tk.DISABLED)
            self.medium_btn.config(state=tk.DISABLED)
            self.hard_btn.config(state=tk.DISABLED)
            
            # Show next card
            self.current_card = self.cards_to_study[0]
            self.front_text.config(state=tk.NORMAL)
            self.front_text.delete(1.0, tk.END)
            self.front_text.insert(tk.END, self.current_card.front)
            self.front_text.config(state=tk.DISABLED)
        else:
            # Study session complete
            self.reset_ui()
            self.message_label.config(text="Study session complete!")
            self.message_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    def reset_ui(self):
        """Reset UI to initial state"""
        # Hide card components
        self.front_text.pack_forget()
        self.back_text.pack_forget()
        
        # Disable buttons
        self.show_answer_btn.config(state=tk.DISABLED)
        self.easy_btn.config(state=tk.DISABLED)
        self.medium_btn.config(state=tk.DISABLED)
        self.hard_btn.config(state=tk.DISABLED)
        
        # Show message label
        self.message_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
