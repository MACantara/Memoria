import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from .base_screen import BaseScreen
from models import FlashcardDecks, Flashcards
import json
from datetime import datetime

class FlashcardScreen(BaseScreen):
    """Screen for managing flashcards in a deck"""
    
    def __init__(self, container, db_session, ui_manager, deck_id):
        self.deck_id = deck_id  # This is the flashcard_deck_id
        super().__init__(container, db_session, ui_manager)
        
    def setup_ui(self):
        # Create top controls
        top_frame = ttk.Frame(self.frame)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Get deck name for title
        try:
            # Use correct primary key field name
            deck = self.db_session.query(FlashcardDecks).filter_by(flashcard_deck_id=self.deck_id).first()
            deck_name = deck.name if deck else f"Deck {self.deck_id}"
        except Exception as e:
            print(f"Error getting deck name: {e}")
            deck_name = f"Deck {self.deck_id}"
        
        # Title
        title_label = ttk.Label(top_frame, text=f"Flashcards: {deck_name}", font=("TkDefaultFont", 16))
        title_label.pack(side=tk.LEFT)
        
        # Back button
        back_btn = ttk.Button(top_frame, text="Back to Decks", command=self.ui_manager.show_decks)
        back_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Add flashcard button
        add_btn = ttk.Button(top_frame, text="Add Flashcard", command=self.add_flashcard)
        add_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Create the treeview for flashcards
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview setup - update column names to match model fields
        columns = ("question", "answer", "created", "due_date")
        self.flashcard_tree = ttk.Treeview(tree_frame, columns=columns, 
                                         show="headings", selectmode="browse")
        self.flashcard_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=self.flashcard_tree.yview)
        self.flashcard_tree.config(yscrollcommand=scrollbar.set)
        
        # Configure columns
        self.flashcard_tree.heading("question", text="Question")
        self.flashcard_tree.heading("answer", text="Answer")
        self.flashcard_tree.heading("created", text="Created")
        self.flashcard_tree.heading("due_date", text="Due Date")
        
        self.flashcard_tree.column("question", width=200)
        self.flashcard_tree.column("answer", width=300)
        self.flashcard_tree.column("created", width=150)
        self.flashcard_tree.column("due_date", width=150)
        
        # Bind double-click to edit flashcard
        self.flashcard_tree.bind("<Double-1>", self.edit_selected_flashcard)
        
        # Add action buttons below the treeview
        actions_frame = ttk.Frame(self.frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.edit_btn = ttk.Button(actions_frame, text="Edit", command=self.edit_flashcard)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_btn = ttk.Button(actions_frame, text="Delete", command=self.delete_flashcard)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
    
    def refresh(self):
        """Load flashcard data from database"""
        # Clear existing items
        for item in self.flashcard_tree.get_children():
            self.flashcard_tree.delete(item)
        
        try:    
            # Get all flashcards for this deck - use correct field names
            flashcards = self.db_session.query(Flashcards).filter_by(flashcard_deck_id=self.deck_id).all()
            
            # Insert into treeview
            for card in flashcards:
                # Format dates - using correct field names
                created = card.created_at.strftime("%Y-%m-%d %H:%M") if card.created_at else ""
                due_date = card.due_date.strftime("%Y-%m-%d %H:%M") if card.due_date else ""
                
                self.flashcard_tree.insert("", "end", values=(
                    card.question,
                    card.correct_answer,
                    created,
                    due_date
                ), tags=(str(card.flashcard_id),))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load flashcards: {str(e)}")
    
    def add_flashcard(self):
        """Add a new flashcard"""
        # Simple implementation - could be expanded with a custom dialog
        question = simpledialog.askstring("Add Flashcard", "Question:")
        if question:
            answer = simpledialog.askstring("Add Flashcard", "Correct Answer:")
            if answer:
                try:
                    # Create new flashcard with correct field names
                    new_card = Flashcards(
                        question=question,
                        correct_answer=answer,
                        incorrect_answers=json.dumps([]),  # Empty JSON array for incorrect answers
                        flashcard_deck_id=self.deck_id,
                        created_at=datetime.utcnow()
                    )
                    
                    # Initialize FSRS state for scheduling
                    if hasattr(new_card, 'init_fsrs_state'):
                        new_card.init_fsrs_state()
                    
                    self.db_session.add(new_card)
                    self.db_session.commit()
                    self.refresh()
                except Exception as e:
                    self.db_session.rollback()
                    messagebox.showerror("Error", f"Failed to create flashcard: {str(e)}")
    
    def edit_flashcard(self):
        """Edit the selected flashcard"""
        selected_item = self.flashcard_tree.selection()
        if selected_item:
            self.edit_selected_flashcard(None, selected_item[0])
    
    def edit_selected_flashcard(self, event=None, item=None):
        """Edit a flashcard when selected"""
        selected_item = item if item else self.flashcard_tree.selection()[0] if self.flashcard_tree.selection() else None
        if not selected_item:
            messagebox.showinfo("No Selection", "Please select a flashcard first")
            return
            
        # Get flashcard ID and current values
        item_id = self.flashcard_tree.item(selected_item)
        card_id = int(item_id["tags"][0])
        current_values = item_id["values"]
        
        # Get updated values from dialog
        new_question = simpledialog.askstring("Edit Flashcard", "Question:", initialvalue=current_values[0])
        if new_question is not None:  # Check for None to handle Cancel button
            new_answer = simpledialog.askstring("Edit Flashcard", "Correct Answer:", initialvalue=current_values[1])
            if new_answer is not None:
                try:
                    # Update flashcard in database - use correct field names
                    card = self.db_session.query(Flashcards).filter_by(flashcard_id=card_id).first()
                    card.question = new_question
                    card.correct_answer = new_answer
                    
                    self.db_session.commit()
                    self.refresh()
                except Exception as e:
                    self.db_session.rollback()
                    messagebox.showerror("Error", f"Failed to update flashcard: {str(e)}")
    
    def delete_flashcard(self):
        """Delete the selected flashcard"""
        selected_item = self.flashcard_tree.selection()
        if not selected_item:
            messagebox.showinfo("No Selection", "Please select a flashcard first")
            return
            
        # Get flashcard ID
        item_id = self.flashcard_tree.item(selected_item[0])
        card_id = int(item_id["tags"][0])
        
        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Delete", 
                                    "Are you sure you want to delete this flashcard?\nThis cannot be undone.")
        if confirm:
            try:
                # Delete the flashcard from database - use correct field name
                card = self.db_session.query(Flashcards).filter_by(flashcard_id=card_id).first()
                self.db_session.delete(card)
                self.db_session.commit()
                self.refresh()
            except Exception as e:
                self.db_session.rollback()
                messagebox.showerror("Error", f"Failed to delete flashcard: {str(e)}")
