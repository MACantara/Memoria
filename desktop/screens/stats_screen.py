import tkinter as tk
from tkinter import ttk
from .base_screen import BaseScreen
from models import FlashcardDecks, Flashcards
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta

class StatsScreen(BaseScreen):
    """Screen for displaying statistics"""
    
    def setup_ui(self):
        # Create main container
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Study Statistics", font=("TkDefaultFont", 16))
        title_label.pack(pady=(0, 20))
        
        # Create a notebook with tabs for different stats
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Overview tab
        self.overview_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_tab, text="Overview")
        
        # Deck tab
        self.deck_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.deck_tab, text="Deck Stats")
        
        # Study History tab
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="Study History")
        
        # Setup each tab
        self.setup_overview_tab()
        self.setup_deck_tab()
        self.setup_history_tab()
        
        # Back button
        back_btn = ttk.Button(main_frame, text="Back to Decks", 
                           command=self.ui_manager.show_decks)
        back_btn.pack(side=tk.LEFT, pady=(10, 0))
        
    def setup_overview_tab(self):
        """Setup the overview statistics tab"""
        # Stats frame
        stats_frame = ttk.Frame(self.overview_tab)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a frame for general stats
        general_frame = ttk.LabelFrame(stats_frame, text="General Statistics")
        general_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create a grid for stats
        for i in range(2):
            general_frame.columnconfigure(i, weight=1)
            
        # Placeholder labels for stats
        stat_labels = [
            ("Total Decks:", "total_decks"),
            ("Total Flashcards:", "total_cards"),
            ("Cards Studied Today:", "studied_today"),
            ("Review Success Rate:", "success_rate")
        ]
        
        # Create labels and store references to value labels
        self.stat_values = {}
        for i, (label_text, value_key) in enumerate(stat_labels):
            row = i // 2
            col = i % 2
            
            frame = ttk.Frame(general_frame)
            frame.grid(row=row, column=col, sticky="ew", padx=10, pady=5)
            
            label = ttk.Label(frame, text=label_text)
            label.pack(side=tk.LEFT)
            
            value = ttk.Label(frame, text="Loading...")
            value.pack(side=tk.RIGHT)
            
            self.stat_values[value_key] = value
            
        # Chart area - placeholder for now
        chart_frame = ttk.LabelFrame(stats_frame, text="Study Overview")
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.fig_overview = plt.Figure(figsize=(5, 4))
        self.canvas_overview = FigureCanvasTkAgg(self.fig_overview, chart_frame)
        self.canvas_overview.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def setup_deck_tab(self):
        """Setup the deck statistics tab"""
        # Top frame for deck selection
        top_frame = ttk.Frame(self.deck_tab)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Deck selection combobox
        deck_label = ttk.Label(top_frame, text="Select Deck:")
        deck_label.pack(side=tk.LEFT)
        
        self.deck_var = tk.StringVar()
        self.deck_combo = ttk.Combobox(top_frame, textvariable=self.deck_var,
                                    state="readonly", width=40)
        self.deck_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.deck_combo.bind("<<ComboboxSelected>>", self.on_deck_selected)
        
        # Stats frame
        stats_frame = ttk.Frame(self.deck_tab)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a frame for deck specific stats
        deck_stats_frame = ttk.LabelFrame(stats_frame, text="Deck Statistics")
        deck_stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create a grid for deck stats
        for i in range(2):
            deck_stats_frame.columnconfigure(i, weight=1)
            
        # Placeholder labels for deck stats
        deck_stat_labels = [
            ("Card Count:", "deck_card_count"),
            ("Studied Cards:", "deck_studied"),
            ("Last Studied:", "deck_last_studied"),
            ("Success Rate:", "deck_success_rate")
        ]
        
        # Create labels and store references to value labels
        self.deck_stat_values = {}
        for i, (label_text, value_key) in enumerate(deck_stat_labels):
            row = i // 2
            col = i % 2
            
            frame = ttk.Frame(deck_stats_frame)
            frame.grid(row=row, column=col, sticky="ew", padx=10, pady=5)
            
            label = ttk.Label(frame, text=label_text)
            label.pack(side=tk.LEFT)
            
            value = ttk.Label(frame, text="Select a deck")
            value.pack(side=tk.RIGHT)
            
            self.deck_stat_values[value_key] = value
            
        # Chart area for deck-specific stats
        deck_chart_frame = ttk.LabelFrame(stats_frame, text="Progress Chart")
        deck_chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.fig_deck = plt.Figure(figsize=(5, 4))
        self.canvas_deck = FigureCanvasTkAgg(self.fig_deck, deck_chart_frame)
        self.canvas_deck.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def setup_history_tab(self):
        """Setup the study history tab"""
        # Filter controls
        filter_frame = ttk.Frame(self.history_tab)
        filter_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Date range selection
        date_label = ttk.Label(filter_frame, text="Date Range:")
        date_label.pack(side=tk.LEFT)
        
        self.date_range = tk.StringVar(value="Last 30 days")
        date_combo = ttk.Combobox(filter_frame, textvariable=self.date_range,
                               state="readonly", width=20)
        date_combo.pack(side=tk.LEFT, padx=5)
        date_combo['values'] = ["Last 7 days", "Last 30 days", "Last 90 days", "All time"]
        date_combo.bind("<<ComboboxSelected>>", self.refresh_history)
        
        # Tree view for study history
        tree_frame = ttk.Frame(self.history_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview for history records
        columns = ("date", "deck", "cards", "time", "performance")
        self.history_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.history_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure the treeview
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("deck", text="Deck")
        self.history_tree.heading("cards", text="Cards Studied")
        self.history_tree.heading("time", text="Study Time")
        self.history_tree.heading("performance", text="Performance")
        
        self.history_tree.column("date", width=120)
        self.history_tree.column("deck", width=200)
        self.history_tree.column("cards", width=100)
        self.history_tree.column("time", width=100)
        self.history_tree.column("performance", width=100)
        
        # Configure scrollbar
        scrollbar.config(command=self.history_tree.yview)
        self.history_tree.config(yscrollcommand=scrollbar.set)
        
    def refresh(self):
        """Refresh all statistics data"""
        self.load_overview_stats()
        self.load_deck_options()
        self.refresh_history()
        
    def load_overview_stats(self):
        """Load general statistics data"""
        try:
            # Get total decks
            total_decks = self.db_session.query(FlashcardDecks).count()
            self.stat_values["total_decks"].config(text=str(total_decks))
            
            # Get total cards
            total_cards = self.db_session.query(Flashcards).count()
            self.stat_values["total_cards"].config(text=str(total_cards))
            
            # For demo purposes, set placeholder values for the rest
            self.stat_values["studied_today"].config(text="0")
            self.stat_values["success_rate"].config(text="N/A")
            
            # Create a simple example chart
            self.update_overview_chart(total_decks, total_cards)
            
        except Exception as e:
            for key in self.stat_values:
                self.stat_values[key].config(text="Error")
            print(f"Error loading overview stats: {e}")
            
    def update_overview_chart(self, total_decks, total_cards):
        """Create a simple chart for the overview tab"""
        self.fig_overview.clear()
        ax = self.fig_overview.add_subplot(111)
        
        # Example data - in a real app, use actual study data
        decks = ['Deck 1', 'Deck 2', 'Deck 3', 'Others']
        sizes = [25, 30, 15, 30]
        
        ax.pie(sizes, labels=decks, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        ax.set_title('Cards by Deck')
        
        self.fig_overview.tight_layout()
        self.canvas_overview.draw()
            
    def load_deck_options(self):
        """Load available decks for the deck stats tab"""
        try:
            # Get all decks
            decks = self.db_session.query(FlashcardDecks).all()
            deck_options = [(deck.id, deck.name) for deck in decks]
            
            # Update combobox
            self.deck_combo['values'] = [name for _, name in deck_options]
            self.deck_ids = [id for id, _ in deck_options]
            
        except Exception as e:
            print(f"Error loading deck options: {e}")
            
    def on_deck_selected(self, event=None):
        """Handle deck selection in the deck stats tab"""
        selected_index = self.deck_combo.current()
        if selected_index >= 0:
            try:
                deck_id = self.deck_ids[selected_index]
                deck = self.db_session.query(FlashcardDecks).get(deck_id)
                
                # Get card count
                card_count = self.db_session.query(Flashcards).filter_by(deck_id=deck_id).count()
                
                # Update stats display
                self.deck_stat_values["deck_card_count"].config(text=str(card_count))
                self.deck_stat_values["deck_studied"].config(text="0")  # Placeholder
                last_studied = deck.last_studied.strftime("%Y-%m-%d") if deck.last_studied else "Never"
                self.deck_stat_values["deck_last_studied"].config(text=last_studied)
                self.deck_stat_values["deck_success_rate"].config(text="N/A")  # Placeholder
                
                # Update deck chart
                self.update_deck_chart(deck_id, deck.name)
                
            except Exception as e:
                for key in self.deck_stat_values:
                    self.deck_stat_values[key].config(text="Error")
                print(f"Error loading deck stats: {e}")
                
    def update_deck_chart(self, deck_id, deck_name):
        """Create a simple chart for the deck tab"""
        self.fig_deck.clear()
        ax = self.fig_deck.add_subplot(111)
        
        # Example data - in a real app, use actual study history
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        studied = [5, 3, 0, 7, 2, 4, 6]
        
        bars = ax.bar(days, studied)
        ax.set_title(f'Study Activity for {deck_name}')
        ax.set_ylabel('Cards Studied')
        
        self.fig_deck.tight_layout()
        self.canvas_deck.draw()
                
    def refresh_history(self, event=None):
        """Refresh the study history display"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        # For demo purposes, add placeholder history data
        # In a real app, you would query the database for actual study sessions
        today = datetime.now()
        
        # Example data points
        sample_data = [
            (today - timedelta(days=1), "Spanish Vocabulary", 20, "15 min", "85%"),
            (today - timedelta(days=2), "Math Formulas", 15, "10 min", "73%"),
            (today - timedelta(days=5), "Biology Terms", 30, "25 min", "90%"),
            (today - timedelta(days=7), "Programming Concepts", 25, "20 min", "82%"),
            (today - timedelta(days=14), "Geography", 15, "12 min", "67%")
        ]
        
        # Filter based on the selected date range
        date_range_text = self.date_range.get()
        if date_range_text == "Last 7 days":
            cutoff = today - timedelta(days=7)
        elif date_range_text == "Last 30 days":
            cutoff = today - timedelta(days=30)
        elif date_range_text == "Last 90 days":
            cutoff = today - timedelta(days=90)
        else:  # All time
            cutoff = today - timedelta(days=365*10)  # Far in the past
            
        # Filter and add to tree
        for date, deck, cards, time, perf in sample_data:
            if date >= cutoff:
                self.history_tree.insert("", "end", values=(
                    date.strftime("%Y-%m-%d"),
                    deck,
                    cards,
                    time,
                    perf
                ))
