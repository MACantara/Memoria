import tkinter as tk
from tkinter import ttk

class BaseScreen:
    """Base class for all screens in the application"""
    
    def __init__(self, container, db_session, ui_manager):
        self.container = container
        self.db_session = db_session
        self.ui_manager = ui_manager
        
        # Create the main frame for this screen
        self.frame = ttk.Frame(self.container)
        self.frame.pack_forget()  # Initially hidden
        
        # Set up UI components
        self.setup_ui()
        
    def setup_ui(self):
        """Set up UI components - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement setup_ui method")
        
    def show(self):
        """Show this screen"""
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.refresh()
        
    def hide(self):
        """Hide this screen"""
        self.frame.pack_forget()
        
    def refresh(self):
        """Refresh data on this screen - to be implemented by subclasses"""
        pass
