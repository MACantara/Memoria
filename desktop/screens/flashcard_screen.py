import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from .base_screen import BaseScreen
from models import FlashcardDecks, Flashcards

class FlashcardScreen(BaseScreen):
    """Screen for managing flashcards in a deck"""
    
    def __init__(self, container, db_session, ui_manager, deck_id):
        self.deck_id = deck_id
        super().__init__(container, db_session, ui_manager)
        
    def setup_ui(self):
        # Create top controls
        top_frame = ttk.Frame(self.frame)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Get deck name for title
        try:
            # Try different attribute names for the primary key
            deck = None
            for attr in ['id', 'deck_id', 'flashcard_deck_id', 'pk']:
                try:
                    deck = self.db_session.query(FlashcardDecks) \
                              .filter(getattr(FlashcardDecks, attr) == self.deck_id).first()
                    if deck:
                        break
                except:
                    continue
            
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
        
        # Treeview setup
        columns = ("front", "back", "created", "due_date")
        self.flashcard_tree = ttk.Treeview(tree_frame, columns=columns, 
                                         show="headings", selectmode="browse")
        self.flashcard_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=self.flashcard_tree.yview)
        self.flashcard_tree.config(yscrollcommand=scrollbar.set)
        
        # Configure columns
        self.flashcard_tree.heading("front", text="Front")
        self.flashcard_tree.heading("back", text="Back")
        self.flashcard_tree.heading("created", text="Created")
        self.flashcard_tree.heading("due_date", text="Due Date")
        
        self.flashcard_tree.column("front", width=200)
        self.flashcard_tree.column("back", width=300)
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
            # Get all flashcards for this deck
            flashcards = self.db_session.query(Flashcards).filter_by(deck_id=self.deck_id).all()
            
            # Insert into treeview
            for card in flashcards:
                # Format dates
                created = card.created.strftime("%Y-%m-%d %H:%M") if card.created else ""
                due_date = card.due_date.strftime("%Y-%m-%d %H:%M") if card.due_date else ""
                
                # Get card ID safely
                card_id = getattr(card, 'id', None) or getattr(card, 'flashcard_id', None) or 0
                
                self.flashcard_tree.insert("", "end", values=(
                    card.front,
                    card.back,
                    created,
                    due_date
                ), tags=(str(card_id),))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load flashcards: {str(e)}")
    
    def add_flashcard(self):
        """Add a new flashcard"""
        # Simple implementation - could be expanded with a custom dialog
        front = simpledialog.askstring("Add Flashcard", "Front (question):")
        if front:
            back = simpledialog.askstring("Add Flashcard", "Back (answer):")
            if back:
                try:
                    # Create new flashcard
                    from datetime import datetime
                    new_card = Flashcards(
                        front=front,
                        back=back,
                        deck_id=self.deck_id,
                        created=datetime.utcnow()
                    )
                    
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
        new_front = simpledialog.askstring("Edit Flashcard", "Front (question):", initialvalue=current_values[0])
        if new_front is not None:  # Check for None to handle Cancel button
            new_back = simpledialog.askstring("Edit Flashcard", "Back (answer):", initialvalue=current_values[1])
            if new_back is not None:
                try:
                    # Update flashcard in database
                    card = self.db_session.query(Flashcards).get(card_id)
                    card.front = new_front
                    card.back = new_back
                    
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
                # Delete the flashcard from database
                card = self.db_session.query(Flashcards).get(card_id)
                self.db_session.delete(card)
                self.db_session.commit()
                self.refresh()
            except Exception as e:
                self.db_session.rollback()
                messagebox.showerror("Error", f"Failed to delete flashcard: {str(e)}")
