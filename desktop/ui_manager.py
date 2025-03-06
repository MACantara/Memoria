import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from datetime import datetime

from desktop.screens.deck_screen import DeckScreen
from desktop.screens.flashcard_screen import FlashcardScreen
from desktop.screens.study_screen import StudyScreen
from desktop.screens.import_screen import ImportScreen
from desktop.screens.stats_screen import StatsScreen
from desktop.screens.generation_screen import GenerationScreen

class UIManager:
    """Manages different UI screens in the application"""
    
    def __init__(self, parent_frame, db_session):
        self.parent = parent_frame
        self.db_session = db_session
        self.current_screen = None
        self.screens = {}
        
        # Initialize screens container
        self.container = ttk.Frame(self.parent)
        self.container.pack(fill=tk.BOTH, expand=True)
        
    def _clear_container(self):
        """Clear the current screen"""
        if self.current_screen:
            self.current_screen.hide()
        
    def show_decks(self):
        """Show the decks screen"""
        self._clear_container()
        
        if 'decks' not in self.screens:
            self.screens['decks'] = DeckScreen(self.container, self.db_session, self)
        
        self.current_screen = self.screens['decks']
        self.current_screen.show()
        
    def show_flashcards(self, deck_id):
        """Show flashcards for a specific deck"""
        self._clear_container()
        
        # Create a new flashcard screen instance for the specific deck
        screen_key = f'flashcards_{deck_id}'
        if screen_key not in self.screens:
            self.screens[screen_key] = FlashcardScreen(self.container, self.db_session, self, deck_id)
        
        self.current_screen = self.screens[screen_key]
        self.current_screen.show()
        
    def create_deck(self):
        """Show create deck dialog"""
        self.show_decks()  # Switch to decks view first
        self.screens['decks'].show_create_dialog()
        
    def show_study(self):
        """Show study screen"""
        self._clear_container()
        
        if 'study' not in self.screens:
            self.screens['study'] = StudyScreen(self.container, self.db_session, self)
            
        self.current_screen = self.screens['study']
        self.current_screen.show()
        
    def show_import_screen(self):
        """Show import screen for flashcards"""
        self._clear_container()
        
        if 'import' not in self.screens:
            self.screens['import'] = ImportScreen(self.container, self.db_session, self)
            
        self.current_screen = self.screens['import']
        self.current_screen.show()
        
    def show_export_screen(self):
        """Show export screen for flashcards"""
        # Implement export functionality
        messagebox.showinfo("Export", "Export functionality will be implemented soon")
        
    def show_stats(self):
        """Show statistics screen"""
        self._clear_container()
        
        if 'stats' not in self.screens:
            self.screens['stats'] = StatsScreen(self.container, self.db_session, self)
            
        self.current_screen = self.screens['stats']
        self.current_screen.show()
        
    def show_generation(self):
        """Show AI generation screen"""
        self._clear_container()
        
        if 'generation' not in self.screens:
            self.screens['generation'] = GenerationScreen(self.container, self.db_session, self)
            
        self.current_screen = self.screens['generation']
        self.current_screen.show()
        
    def refresh_current_screen(self):
        """Refresh the current screen"""
        if self.current_screen:
            self.current_screen.refresh()
