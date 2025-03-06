import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .base_screen import BaseScreen
from models import FlashcardDecks, Flashcards
import json
from datetime import datetime

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
        """Import flashcards from file"""
        file_path = self.file_path_var.get()
        
        if not file_path:
            messagebox.showerror("Error", "Please select a file to import")
            return
        
        try:
            # Get or create deck
            deck_id = self._get_target_deck(self.new_deck_var, self.new_deck_name_var,
                                        self.deck_combo, self.file_deck_ids)
            
            if deck_id is None:
                return
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process content
            flashcards = self._parse_content(content)
            
            if not flashcards:
                self.file_status_var.set("No valid flashcards found in the file")
                return
                
            # Create flashcards using the correct field names
            now = datetime.now()
            for front, back in flashcards:
                card = Flashcards(
                    question=front,
                    correct_answer=back,
                    incorrect_answers=json.dumps([]),  # Empty JSON array for incorrect answers
                    flashcard_deck_id=deck_id,
                    created_at=now
                )
                # Initialize FSRS state for scheduling if available
                if hasattr(card, 'init_fsrs_state'):
                    card.init_fsrs_state()
                    
                self.db_session.add(card)
                
            self.db_session.commit()
            self.file_status_var.set(f"Successfully imported {len(flashcards)} flashcards")
            self.refresh()
        except Exception as e:
            self.db_session.rollback()
            self.file_status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Import Error", str(e))
    
    def import_text(self):
        """Import flashcards from pasted text"""
        content = self.text_area.get(1.0, tk.END)
        
        if not content.strip():
            messagebox.showerror("Error", "Please enter or paste some text to import")
            return
        
        try:
            # Get or create deck
            deck_id = self._get_target_deck(self.new_text_deck_var, self.new_text_deck_name_var,
                                        self.text_deck_combo, self.text_deck_ids)
            
            if deck_id is None:
                return
            
            # Process content
            flashcards = self._parse_content(content)
            
            if not flashcards:
                self.text_status_var.set("No valid flashcards found in the text")
                return
                
            # Create flashcards with correct field names
            now = datetime.now()
            for front, back in flashcards:
                card = Flashcards(
                    question=front,
                    correct_answer=back,
                    incorrect_answers=json.dumps([]),  # Empty JSON array for incorrect answers
                    flashcard_deck_id=deck_id,
                    created_at=now
                )
                # Initialize FSRS state for scheduling if available
                if hasattr(card, 'init_fsrs_state'):
                    card.init_fsrs_state()
                    
                self.db_session.add(card)
                
            self.db_session.commit()
            self.text_status_var.set(f"Successfully imported {len(flashcards)} flashcards")
            self.refresh()
        except Exception as e:
            self.db_session.rollback()
            self.text_status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Import Error", str(e))
