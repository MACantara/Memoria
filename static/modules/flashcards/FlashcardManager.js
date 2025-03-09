import { shuffleArray, updateProgress } from '../utils.js';
import { UIManager } from './UIManager.js';
import { NavigationManager } from './NavigationManager.js';
import { EventManager } from './EventManager.js';

export class FlashcardManager {
    constructor() {
        this.container = document.getElementById('flashcardsContainer');
        this.currentCardIndex = 0;
        this.score = 0;  // Track cards completed in this session
        this.flashcards = [];  // Store flashcard data, not DOM elements
        this.ui = new UIManager();
        this.completedCards = new Set();  // Track cards completed in this session
        this.totalDueCards = parseInt(document.getElementById('totalFlashcards')?.value || 0);
        this.deckId = document.getElementById('deckId')?.value;
        this.studyMode = document.getElementById('studyMode')?.value === 'due_only';
        this.isLoading = false;
        this.currentCard = null;  // Store the current card data
        
        // Initialize event system
        this.eventListeners = {};
        
        // Initialize navigation and event managers
        this.navigation = new NavigationManager(this);
        this.events = new EventManager(this, this.ui);
        
        // Make this instance available globally for event handlers
        window.flashcardManager = this;
        
        // Log the total due cards for debugging
        console.log(`Total cards to study: ${this.totalDueCards}`);
    }

    // Add event listener system
    addEventListener(eventName, callback) {
        if (!this.eventListeners[eventName]) {
            this.eventListeners[eventName] = [];
        }
        this.eventListeners[eventName].push(callback);
    }

    removeEventListener(eventName, callback) {
        if (this.eventListeners[eventName]) {
            this.eventListeners[eventName] = this.eventListeners[eventName].filter(
                cb => cb !== callback
            );
        }
    }

    dispatchEvent(eventName, data) {
        if (this.eventListeners[eventName]) {
            this.eventListeners[eventName].forEach(callback => {
                callback(data);
            });
        }
    }

    async initialize() {
        if (!this.container) return;
        
        console.log(`Initializing flashcard manager. Total expected cards: ${this.totalDueCards}`);
        
        if (this.totalDueCards > 0) {
            // Load all flashcards at once
            await this.loadAllFlashcards();
            
            // Show the first card if we loaded any
            if (this.flashcards.length > 0) {
                this.currentCardIndex = 0;
                this.currentCard = this.flashcards[0];
                this.ui.renderCard(this.currentCard);
                this.updateCardCounter();
                
                // Update the total count with the actual cards loaded
                this.totalDueCards = this.flashcards.length;
                
                // Dispatch event when cards are loaded
                this.dispatchEvent('firstBatchLoaded');
                
                // Hide the initial loading indicator
                const initialLoader = document.getElementById('initialLoadingIndicator');
                if (initialLoader) {
                    initialLoader.classList.add('d-none');
                }
                
                // Show the first card
                const currentCard = document.getElementById('currentFlashcard');
                if (currentCard) {
                    currentCard.style.display = 'block';
                }
            } else {
                // No cards were loaded, show a message
                this.ui.showNoCardsMessage();
            }
        }
        
        // Update the initial score and progress display
        this.ui.updateScore(this.score, this.totalDueCards);
        
        // Setup event listeners
        this.events.setupEventListeners();
    }

    async loadAllFlashcards() {
        try {
            if (this.isLoading) return;
            
            this.isLoading = true;
            this.ui.showLoading(true);
            
            // Build the URL for loading all cards at once
            const url = new URL(`/deck/study/${this.deckId}`, window.location.origin);
            
            // Add query parameter for due only
            if (this.studyMode) {
                url.searchParams.append('due_only', 'true');
            }
            
            console.log(`Loading all flashcards from: ${url}`);
            
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`Server returned ${response.status}: ${errorText}`);
                throw new Error(`Network response was not ok (${response.status})`);
            }
            
            const data = await response.json();
            
            // Store all flashcards
            this.flashcards = data.flashcards;
            console.log(`Successfully loaded ${this.flashcards.length} flashcards`);
            
            // Update the total now that we know the actual count
            if (this.flashcards.length !== this.totalDueCards) {
                console.log(`Updating total from ${this.totalDueCards} to ${this.flashcards.length}`);
                this.totalDueCards = this.flashcards.length;
            }
            
        } catch (error) {
            console.error("Error loading flashcards:", error);
            this.ui.showLoadingError(error.message);
        } finally {
            this.isLoading = false;
            this.ui.showLoading(false);
        }
    }

    updateCardCounter() {
        // Calculate cards left to review in this session
        const remaining = Math.max(0, this.totalDueCards - this.score);
        
        // Use getDisplayIndex to get the correct 1-based card number for display
        const currentIndex = this.getDisplayIndex(this.currentCardIndex);
        
        // Update UI manager's counter with correct display index
        this.ui.updateCardCounter(currentIndex - 1, this.totalDueCards, this.score, remaining);
        
        // Log counter state for debugging
        console.log(`Card counter: ${this.score}/${this.totalDueCards}, ${remaining} remaining`);
    }

    async moveToNextCard() {
        // Debug info
        console.log("Moving to next card. Completed cards:", this.completedCards.size);
        console.log(`Total cards to review: ${this.totalDueCards}, completed: ${this.score}`);
        
        // Find the next uncompleted card
        for (let i = 0; i < this.flashcards.length; i++) {
            // Skip current card
            if (i === this.currentCardIndex) continue;
            
            const card = this.flashcards[i];
            const cardState = parseInt(card.state || 0);
            
            // In "Study All" mode, show any card that hasn't been completed in this session
            // In "Due Only" mode, only show cards that aren't mastered and haven't been completed
            if (!this.completedCards.has(card.id) && 
                (!this.studyMode || cardState !== 2)) {
                
                this.currentCardIndex = i;
                this.currentCard = card;
                const visibleCardIndex = this.getDisplayIndex(i);
                console.log(`Moving to card ${visibleCardIndex}/${this.totalDueCards} with ID ${card.id}`);
                
                // Render this card
                this.ui.renderCard(card);
                this.updateCardCounter();
                return;
            }
        }
        
        // If we reach here, all cards have been completed
        console.log("All cards completed. Showing completion screen.");
        this.checkRemainingDueCards();
    }

    async handleAnswer(selectedAnswer) {
        // Prevent multiple submissions while processing
        if (this.isProcessingAnswer) return;
        this.isProcessingAnswer = true;
        
        const card = this.currentCard;
        if (!card) return;
        
        const isCorrect = selectedAnswer === card.correct_answer;
        
        try {
            // Update server-side progress first
            const result = await updateProgress(card.id, isCorrect);
            
            if (result.success) {
                // Update FSRS specific data in our cached data
                card.state = this.getFsrsStateNumber(result.state);
                card.retrievability = result.retrievability || 0;
            }
        } catch (error) {
            console.error("Failed to update progress:", error);
        }
        
        // Mark this card as completed in this session (regardless of correctness)
        if (!this.completedCards.has(card.id)) {
            this.completedCards.add(card.id);
            this.score++;
            
            // Debug info
            console.log(`Card ${card.id} completed. Score: ${this.score}/${this.totalDueCards}`);
            console.log(`Completed cards: ${this.completedCards.size}, Total flashcards: ${this.flashcards.length}`);
            
            // Update the progress display
            this.ui.updateScore(this.score, this.totalDueCards);
        }
        
        // Show different feedback based on correctness
        if (isCorrect) {
            // For correct answers, show brief feedback then auto-advance
            this.ui.showBriefFeedback(true);
            
            // Set a short timeout to auto-advance
            setTimeout(() => {
                // If all cards are completed, show completion screen
                if (this.completedCards.size >= this.totalDueCards) {
                    console.log("All cards completed. Showing completion screen.");
                    this.checkRemainingDueCards();
                } else {
                    // Otherwise move to the next card
                    this.moveToNextCard();
                }
            }, 1000); // Show success for 1 second before advancing
        } else {
            // For incorrect answers, show feedback with "Next" button
            this.ui.showAnswerFeedback(false, () => {
                // This callback is triggered when the user clicks "Next"
                
                // Add card back to the end of the queue for review
                this.moveCardToEnd(card);
                
                // If all cards are completed, show completion screen
                if (this.completedCards.size >= this.totalDueCards) {
                    console.log("All cards completed. Showing completion screen.");
                    this.checkRemainingDueCards();
                } else {
                    // Otherwise move to the next card
                    this.moveToNextCard();
                }
            });
        }
        
        // Reset processing flag
        this.isProcessingAnswer = false;
    }

    moveCardToEnd(card) {
        // Remove the card from its current position
        this.flashcards.splice(this.currentCardIndex, 1);
        
        // Insert it at the end
        this.flashcards.push(card);
        
        // Adjust currentCardIndex if needed (if we removed a card before the current position)
        if (this.currentCardIndex > 0) {
            this.currentCardIndex--;
        }
    }

    getFsrsStateNumber(stateName) {
        const stateMap = {
            'new': 0,
            'learning': 1,
            'mastered': 2,
            'forgotten': 3,
            // Default to 0 if unknown
            'unknown': 0
        };
        return stateMap[stateName] || 0;
    }

    getDisplayIndex(arrayIndex) {
        // Count how many uncompleted cards appear before this index
        let displayIndex = 1; // Start at 1 for 1-based indexing
        
        for (let i = 0; i < arrayIndex; i++) {
            if (i < this.flashcards.length && !this.completedCards.has(this.flashcards[i].id)) {
                displayIndex++;
            }
        }
        
        return displayIndex;
    }

    handleKeyboardNavigation(key) {
        this.navigation.handleKeyPress(key);
    }

    checkRemainingDueCards() {
        // Get the current study mode
        const isDueOnly = this.studyMode;
        
        // Make sure score reflects completion - set score to total cards
        this.score = this.completedCards.size;
        
        // Update UI to show all cards completed and 0 remaining
        this.ui.updateScore(this.score, this.totalDueCards);
        this.ui.updateCardCounter(this.score - 1, this.totalDueCards, this.score, 0);
        
        // In "Study All" mode, we know we've completed everything, so no need to check server
        if (!isDueOnly) {
            this.ui.showCompletionScreen(this.deckId, this.score, this.totalDueCards, isDueOnly, 0);
            return;
        }
        
        // In "Due Only" mode, check if there are more due cards that were added since we started
        fetch(`/deck/api/due-count/${this.deckId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const remainingDueCards = data.due_count;
                    console.log(`Remaining due cards: ${remainingDueCards}`);
                    
                    // Display completion with information about remaining due cards
                    this.ui.showCompletionScreen(this.deckId, this.score, this.totalDueCards, isDueOnly, remainingDueCards);
                } else {
                    // Error fetching due count, just show normal completion
                    this.ui.showCompletionScreen(this.deckId, this.score, this.totalDueCards, isDueOnly, 0);
                }
            })
            .catch(error => {
                console.error("Error checking remaining due cards:", error);
                // Error occurred, just show normal completion
                this.ui.showCompletionScreen(this.deckId, this.score, this.totalDueCards, isDueOnly, 0);
            });
    }
}
