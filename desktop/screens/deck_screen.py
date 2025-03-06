import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from .base_screen import BaseScreen
from models import FlashcardDecks, db

class DeckScreen(BaseScreen):
    """Screen for displaying and managing flashcard decks"""
    
    def setup_ui(self):
        # Create top controls
        top_frame = ttk.Frame(self.frame)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(top_frame, text="Flashcard Decks", font=("TkDefaultFont", 16))
        title_label.pack(side=tk.LEFT)
        
        # Create deck button
        create_btn = ttk.Button(top_frame, text="Create New Deck", 
                               command=self.show_create_dialog)
        create_btn.pack(side=tk.RIGHT)
        
        # Create the treeview for decks
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview setup
        columns = ("name", "description", "card_count", "last_studied")
        self.deck_tree = ttk.Treeview(tree_frame, columns=columns, 
                                    show="headings", selectmode="browse")
        self.deck_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=self.deck_tree.yview)
        self.deck_tree.config(yscrollcommand=scrollbar.set)
        
        # Configure columns
        self.deck_tree.heading("name", text="Deck Name")
        self.deck_tree.heading("description", text="Description")
        self.deck_tree.heading("card_count", text="Cards")
        self.deck_tree.heading("last_studied", text="Last Studied")
        
        self.deck_tree.column("name", width=200)
        self.deck_tree.column("description", width=300)
        self.deck_tree.column("card_count", width=80)
        self.deck_tree.column("last_studied", width=150)
        
        # Bind double-click to open deck
        self.deck_tree.bind("<Double-1>", self.open_selected_deck)
        
        # Add action buttons below the treeview
        actions_frame = ttk.Frame(self.frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.view_btn = ttk.Button(actions_frame, text="View Cards", command=self.view_selected_deck)
        self.view_btn.pack(side=tk.LEFT, padx=5)
        
        self.study_btn = ttk.Button(actions_frame, text="Study Now", command=self.study_selected_deck)
        self.study_btn.pack(side=tk.LEFT, padx=5)
        
        self.edit_btn = ttk.Button(actions_frame, text="Edit", command=self.edit_selected_deck)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_btn = ttk.Button(actions_frame, text="Delete", command=self.delete_selected_deck)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        
    def refresh(self):
        """Load deck data from database"""
        # Clear existing items
        for item in self.deck_tree.get_children():
            self.deck_tree.delete(item)
            
        # Get all decks from the database
        decks = self.db_session.query(FlashcardDecks).all()
        
        # Insert into treeview
        for deck in decks:
            # Get card count for this deck
            card_count = self.db_session.query(db.func.count()).filter_by(deck_id=deck.id).scalar()
            
            # Format last studied date
            last_studied = deck.last_studied.strftime("%Y-%m-%d %H:%M") if deck.last_studied else "Never"
            
            self.deck_tree.insert("", "end", values=(
                deck.name,
                deck.description or "",
                card_count,
                last_studied
            ), tags=(str(deck.id),))
            
    def show_create_dialog(self):
        """Show dialog to create a new deck"""
        name = simpledialog.askstring("Create Deck", "Enter deck name:")
        if name:
            description = simpledialog.askstring("Create Deck", "Enter deck description (optional):")
            
            # Create new deck
            new_deck = FlashcardDecks(
                name=name,
                description=description if description else None
            )
            
            try:
                self.db_session.add(new_deck)
                self.db_session.commit()
                self.refresh()
            except Exception as e:
                self.db_session.rollback()
                messagebox.showerror("Error", f"Failed to create deck: {str(e)}")
    
    def open_selected_deck(self, event=None):
        """Open the selected deck to view its flashcards"""
        self.view_selected_deck()
        
    def view_selected_deck(self):
        """View flashcards in the selected deck"""
        selected_item = self.deck_tree.selection()
        if not selected_item:
            messagebox.showinfo("No Selection", "Please select a deck first")
            return
            
        # Get deck ID from the item tags
        item_id = self.deck_tree.item(selected_item[0])
        deck_id = int(item_id["tags"][0])
        
        # Show the flashcards screen for this deck
        self.ui_manager.show_flashcards(deck_id)
    
    def study_selected_deck(self):
        """Study the selected deck"""
        selected_item = self.deck_tree.selection()
        if not selected_item:
            messagebox.showinfo("No Selection", "Please select a deck first")
            return
            
        # Get deck ID from the item tags
        item_id = self.deck_tree.item(selected_item[0])
        deck_id = int(item_id["tags"][0])
        
        # Show the study screen for this deck
        # This would need to be implemented in the UIManager
        messagebox.showinfo("Study", f"Study functionality for deck {deck_id} will be implemented soon")
    
    def edit_selected_deck(self):
        """Edit the selected deck"""
        selected_item = self.deck_tree.selection()
        if not selected_item:
            messagebox.showinfo("No Selection", "Please select a deck first")
            return
            
        # Get deck ID and current values
        item_id = self.deck_tree.item(selected_item[0])
        deck_id = int(item_id["tags"][0])
        current_values = item_id["values"]
        
        # Get updated values from dialog
        new_name = simpledialog.askstring("Edit Deck", "Deck name:", initialvalue=current_values[0])
        if new_name:
            new_desc = simpledialog.askstring("Edit Deck", "Description:", initialvalue=current_values[1] or "")
            
            try:
                # Update deck in database
                deck = self.db_session.query(FlashcardDecks).get(deck_id)
                deck.name = new_name
                deck.description = new_desc if new_desc else None
                
                self.db_session.commit()
                self.refresh()
            except Exception as e:
                self.db_session.rollback()
                messagebox.showerror("Error", f"Failed to update deck: {str(e)}")
    
    def delete_selected_deck(self):
        """Delete the selected deck"""
        selected_item = self.deck_tree.selection()
        if not selected_item:
            messagebox.showinfo("No Selection", "Please select a deck first")
            return
            
        # Get deck ID
        item_id = self.deck_tree.item(selected_item[0])
        deck_id = int(item_id["tags"][0])
        deck_name = item_id["values"][0]
        
        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Delete", 
                                    f"Are you sure you want to delete '{deck_name}'?\n\nThis will delete all flashcards in this deck and cannot be undone.")
        if confirm:
            try:
                # Delete the deck from database
                deck = self.db_session.query(FlashcardDecks).get(deck_id)
                self.db_session.delete(deck)
                self.db_session.commit()
                self.refresh()
            except Exception as e:
                self.db_session.rollback()
                messagebox.showerror("Error", f"Failed to delete deck: {str(e)}")
