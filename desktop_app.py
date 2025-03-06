import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from config import Config
from models import db, FlashcardDecks, Flashcards
from sqlalchemy.orm import scoped_session, sessionmaker
from desktop.ui_manager import UIManager

class MemoriaDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Memoria - Flashcard Application")
        self.root.geometry("1000x700")
        
        # Set up database
        self.setup_database()
        
        # Create main frame for content
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Initialize UI Manager
        self.ui_manager = UIManager(self.main_frame, self.db_session)
        
        # Set up menu
        self.setup_menu()
        
    def setup_database(self):
        """Set up database connection for desktop application"""
        from sqlalchemy import create_engine
        
        # Use the same database configuration as the web app
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        db.metadata.create_all(engine)
        
        # Create a session factory
        session_factory = sessionmaker(bind=engine)
        self.db_session = scoped_session(session_factory)
        
    def setup_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Import Flashcards", command=self.ui_manager.show_import_screen)
        file_menu.add_command(label="Export Flashcards", command=self.ui_manager.show_export_screen)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Decks menu
        decks_menu = tk.Menu(menubar, tearoff=0)
        decks_menu.add_command(label="View All Decks", command=self.ui_manager.show_decks)
        decks_menu.add_command(label="Create New Deck", command=self.ui_manager.create_deck)
        menubar.add_cascade(label="Decks", menu=decks_menu)
        
        # Flashcards menu
        cards_menu = tk.Menu(menubar, tearoff=0)
        cards_menu.add_command(label="Study", command=self.ui_manager.show_study)
        cards_menu.add_command(label="Generate Flashcards", command=self.ui_manager.show_generation)
        menubar.add_cascade(label="Flashcards", menu=cards_menu)
        
        # Stats menu
        stats_menu = tk.Menu(menubar, tearoff=0)
        stats_menu.add_command(label="View Statistics", command=self.ui_manager.show_stats)
        menubar.add_cascade(label="Statistics", menu=stats_menu)
        
        self.root.config(menu=menubar)
        
    def run(self):
        """Run the application main loop"""
        # Show the deck list by default
        self.ui_manager.show_decks()
        self.root.mainloop()
        
        # Clean up database session when app closes
        self.db_session.remove()

if __name__ == "__main__":
    root = tk.Tk()
    app = MemoriaDesktopApp(root)
    app.run()
