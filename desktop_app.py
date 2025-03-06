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
        
        # Create engine with minimal connection pooling
        # This reduces the number of connections used
        connection_args = {
            'pool_size': 1,            # Use only one connection
            'max_overflow': 0,         # Don't allow additional connections
            'pool_timeout': 30,        # Connection timeout in seconds
            'pool_recycle': 1800,      # Recycle connections after 30 minutes
            'pool_pre_ping': True      # Verify connection is still valid before using
        }
        
        engine = create_engine(
            Config.SQLALCHEMY_DATABASE_URI,
            **connection_args
        )
        
        # Create tables if they don't exist
        # This only runs once when the app starts
        db.metadata.create_all(engine)
        
        # Create a session factory with a scoped session
        # This ensures we use the same session throughout the app
        session_factory = sessionmaker(bind=engine)
        self.db_session = scoped_session(session_factory)
        
        # Add a method to the session to refresh it if it gets disconnected
        def refresh_session():
            try:
                # Test if connection is valid
                self.db_session.execute("SELECT 1")
            except Exception:
                # If not, recycle the connection
                self.db_session.remove()
                
        # Add the refresh method to be accessible later
        self.db_session.refresh = refresh_session
        
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
        
        # Register cleanup handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.root.mainloop()
        
    def on_close(self):
        """Clean up resources when application closes"""
        # Clean up database session
        try:
            self.db_session.remove()
        except:
            pass
        
        # Close the window
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MemoriaDesktopApp(root)
    app.run()
