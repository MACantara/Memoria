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
        
        this.batchSize = 25; // Default batch size
        this.currentPage = 1; // Track current page for pagination
        this.isLastBatch = false; // Flag to indicate if we've loaded the last batch
        this.isLoadingBatch = false; // Flag to prevent concurrent batch loading
        
        // Initialize event system
        this.eventListeners = {};
        
        // Initialize navigation and event managers
        this.navigation = new NavigationManager(this);
        this.events = new EventManager(this, this.ui);
        
        // Make this instance available globally for event handlers
        window.flashcardManager = this;
        
        // Log the total due cards for debugging
        console.log(`Total cards to study: ${this.totalDueCards}`);
        
        // Initialize delete card modal
        this.deleteCardModal = new bootstrap.Modal(document.getElementById('deleteCardModal'));
        this.setupDeleteCardHandlers();
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
            // Load first batch of flashcards instead of all at once
            await this.loadFlashcardBatch();
            
            // Initialize milestone segments
            this.ui.initializeMilestones(this.totalDueCards);
            
            // Show the first card if we loaded any
            if (this.flashcards.length > 0) {
                this.currentCardIndex = 0;
                this.currentCard = this.flashcards[0];
                
                // Hide loading indicator and show the first card
                const loadingContainer = document.getElementById('loadingContainer');
                if (loadingContainer) {
                    loadingContainer.style.display = 'none';
                }
                
                const currentCard = document.getElementById('currentFlashcard');
                if (currentCard) {
                    currentCard.style.display = 'block';
                    // Add the current flashcard ID as a data attribute
                    currentCard.dataset.flashcardId = this.currentCard.id;
                }
                
                this.ui.renderCard(this.currentCard);
                this.updateCardCounter();
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

    async loadFlashcardBatch() {
        try {
            if (this.isLoadingBatch || this.isLastBatch) return;
            
            this.isLoadingBatch = true;
            console.log(`Loading batch ${this.currentPage} (size: ${this.batchSize})`);
            
            // Show loading indicator for subsequent batches (not the first one)
            if (this.currentPage > 1) {
                this.ui.showLoading(true);
            }
            
            // Build the URL with pagination parameters
            const url = new URL(`/deck/study/${this.deckId}`, window.location.origin);
            
            // Add query parameters
            url.searchParams.append('page', this.currentPage);
            url.searchParams.append('per_page', this.batchSize);
            
            if (this.studyMode) {
                url.searchParams.append('due_only', 'true');
            }
            
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
            
            // Add the new batch of cards to our existing cards
            this.flashcards = [...this.flashcards, ...data.flashcards];
            
            console.log(`Loaded batch ${this.currentPage}: ${data.flashcards.length} cards (total now: ${this.flashcards.length})`);
            
            // Update total count with server's value
            if (this.totalDueCards !== data.total) {
                console.log(`Updating total from ${this.totalDueCards} to ${data.total}`);
                this.totalDueCards = data.total;
                
                // Update milestone display with new total
                this.ui.initializeMilestones(this.totalDueCards);
            }
            
            // Check if this is the last batch
            if (data.flashcards.length < this.batchSize || this.flashcards.length >= data.total) {
                console.log('Reached last batch of cards');
                this.isLastBatch = true;
            }
            
            // Increment page for next batch
            this.currentPage++;
            
            // Dispatch event after first batch is loaded
            if (this.currentPage === 2) {
                this.dispatchEvent('firstBatchLoaded');
            }
            
            // Hide loading indicator for subsequent batches
            if (this.currentPage > 2) {
                this.ui.showLoading(false);
            }
            
            return data.flashcards;
            
        } catch (error) {
            console.error("Error loading flashcards:", error);
            this.ui.showLoadingError(error.message);
            return [];
        } finally {
            this.isLoadingBatch = false;
        }
    }

    async loadAllFlashcards() {
        return this.loadFlashcardBatch();
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
        
        // Find the earliest due card that hasn't been completed yet
        let nextCardIndex = -1;
        let earliestDueDate = null;
        
        for (let i = 0; i < this.flashcards.length; i++) {
            const card = this.flashcards[i];
            const cardState = parseInt(card.state || 0);
            
            // Skip completed cards
            if (this.completedCards.has(card.id)) continue;
            
            // In "Due Only" mode, skip mastered cards
            if (this.studyMode && cardState === 2) continue;
            
            // Convert due date string to Date object for comparison
            // If no due date, treat as earliest possible date (beginning of time)
            const cardDueDate = card.due_date ? new Date(card.due_date) : new Date(0);
            
            // If this is the first valid card we've found, or it's due earlier than our current earliest
            if (nextCardIndex === -1 || cardDueDate < earliestDueDate) {
                nextCardIndex = i;
                earliestDueDate = cardDueDate;
            }
        }
        
        // If we found a valid next card
        if (nextCardIndex !== -1) {
            this.currentCardIndex = nextCardIndex;
            this.currentCard = this.flashcards[nextCardIndex];
            const visibleCardIndex = this.getDisplayIndex(nextCardIndex);
            console.log(`Moving to card ${visibleCardIndex}/${this.totalDueCards} with ID ${this.currentCard.id} (due: ${this.currentCard.due_date || 'N/A'})`);
            
            // Add the current flashcard ID as a data attribute
            const currentCardElement = document.getElementById('currentFlashcard');
            if (currentCardElement) {
                currentCardElement.dataset.flashcardId = this.currentCard.id;
            }
            
            // Render this card
            this.ui.renderCard(this.currentCard);
            this.updateCardCounter();
            return;
        }
        
        // If we haven't loaded all cards yet, load the next batch
        if (!this.isLastBatch && this.completedCards.size < this.totalDueCards) {
            console.log("No cards found in current batch, loading next batch...");
            const newCards = await this.loadFlashcardBatch();
            
            // If we loaded new cards, try again to find the next card
            if (newCards && newCards.length > 0) {
                return this.moveToNextCard();
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
        
        // Update the due date to reschedule the card
        // If the card has a due_date, add a small delay (5 minutes) to push it back
        // This ensures it comes after currently due cards but before far-future cards
        const now = new Date();
        const updatedDueDate = new Date(now.getTime() + 5 * 60 * 1000); // now + 5 minutes
        card.due_date = updatedDueDate.toISOString();
        
        // Find the right insertion point based on due date
        // Cards are ordered by due date, so insert after all currently due cards
        // but before cards due further in the future
        let insertIndex = this.flashcards.length; // Default to end
        
        for (let i = 0; i < this.flashcards.length; i++) {
            // Skip completed cards at beginning of search
            if (this.completedCards.has(this.flashcards[i].id)) continue;
            
            const otherCardDueDate = this.flashcards[i].due_date ? 
                new Date(this.flashcards[i].due_date) : new Date(0);
            
            if (otherCardDueDate > updatedDueDate) {
                insertIndex = i;
                break;
            }
        }
        
        // Insert the card at the appropriate position
        this.flashcards.splice(insertIndex, 0, card);
        
        console.log(`Card ${card.id} rescheduled to ${card.due_date} and inserted at position ${insertIndex}`);
        
        // Adjust currentCardIndex if needed
        if (this.currentCardIndex > insertIndex) {
            this.currentCardIndex++;
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

    /**
     * Show the edit modal for a flashcard
     * @param {string} flashcardId - The ID of the flashcard to edit
     */
    showEditModal(flashcardId) {
        // Get the current card
        const card = this.currentCard;
        if (!card || card.id != flashcardId) return;
        
        // Check if modal is already open
        const modalElement = document.getElementById('editFlashcardModal');
        if (modalElement && modalElement.classList.contains('show')) {
            console.log('Edit modal is already open');
            return;
        }
        
        // Get modal elements
        const editModal = new bootstrap.Modal(document.getElementById('editFlashcardModal'));
        const form = document.getElementById('editFlashcardForm');
        const idInput = document.getElementById('editFlashcardId');
        const questionInput = document.getElementById('editFlashcardQuestion');
        const correctAnswerInput = document.getElementById('editFlashcardCorrectAnswer');
        const incorrectContainer = document.getElementById('editIncorrectAnswersContainer');
        
        if (!form || !idInput || !questionInput || !correctAnswerInput || !incorrectContainer) {
            console.error('Edit modal elements not found');
            return;
        }
        
        // Populate form
        idInput.value = card.id;
        questionInput.value = card.question;
        correctAnswerInput.value = card.correct_answer;
        
        // Clear container
        incorrectContainer.innerHTML = '';
        
        // Add incorrect answers
        card.incorrect_answers.forEach((answer, index) => {
            incorrectContainer.innerHTML += `
                <div class="mb-2">
                    <textarea class="form-control mb-2" name="incorrect_answers[]" rows="2" required 
                             placeholder="Incorrect Answer ${index + 1}">${answer || ''}</textarea>
                </div>
            `;
        });
        
        // Make sure we have at least 3 options
        while (incorrectContainer.children.length < 3) {
            incorrectContainer.innerHTML += `
                <div class="mb-2">
                    <textarea class="form-control mb-2" name="incorrect_answers[]" rows="2" required 
                             placeholder="Incorrect Answer ${incorrectContainer.children.length + 1}"></textarea>
                </div>
            `;
        }
        
        // Clear status area
        document.getElementById('editFlashcardStatus').innerHTML = '';
        
        // Assign update handler to the button
        const updateBtn = document.getElementById('updateFlashcardBtn');
        if (updateBtn) {
            // Remove existing event listeners
            const newBtn = updateBtn.cloneNode(true);
            updateBtn.parentNode.replaceChild(newBtn, updateBtn);
            
            // Add new event listener
            newBtn.addEventListener('click', async () => {
                await this.updateFlashcard();
            });
        }
        
        // Show modal
        editModal.show();
    }
    
    /**
     * Update a flashcard based on the edit form
     */
    async updateFlashcard() {
        const form = document.getElementById('editFlashcardForm');
        const statusDiv = document.getElementById('editFlashcardStatus');
        const button = document.getElementById('updateFlashcardBtn');
        const normalState = button.querySelector('.normal-state');
        const loadingState = button.querySelector('.loading-state');
        
        // Basic validation
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        // Show loading state
        button.disabled = true;
        normalState.classList.add('d-none');
        loadingState.classList.remove('d-none');
        
        // Collect form data
        const flashcardId = document.getElementById('editFlashcardId').value;
        const question = document.getElementById('editFlashcardQuestion').value;
        const correctAnswer = document.getElementById('editFlashcardCorrectAnswer').value;
        const incorrectAnswers = Array.from(form.querySelectorAll('textarea[name="incorrect_answers[]"]'))
            .map(ta => ta.value);
        
        try {
            // Send API request
            const response = await fetch(`/flashcard/update/${flashcardId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: question,
                    correct_answer: correctAnswer,
                    incorrect_answers: incorrectAnswers
                }),
            });
            
            const result = await response.json();
            
            if (response.ok) {
                statusDiv.innerHTML = `
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle me-2"></i> Flashcard updated successfully!
                    </div>
                `;
                
                // Update the current card in memory
                if (this.currentCard && this.currentCard.id == flashcardId) {
                    this.currentCard.question = question;
                    this.currentCard.correct_answer = correctAnswer;
                    this.currentCard.incorrect_answers = incorrectAnswers;
                    
                    // Re-render the current card to show changes
                    this.ui.renderCard(this.currentCard);
                }
                
                // Close the modal after a short delay
                setTimeout(() => {
                    const editModal = bootstrap.Modal.getInstance(document.getElementById('editFlashcardModal'));
                    if (editModal) {
                        editModal.hide();
                    }
                }, 1500);
            } else {
                throw new Error(result.error || 'Failed to update flashcard');
            }
        } catch (error) {
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i> ${error.message}
                </div>
            `;
        } finally {
            // Restore button state
            button.disabled = false;
            normalState.classList.remove('d-none');
            loadingState.classList.add('d-none');
        }
    }

    setupDeleteCardHandlers() {
        const topRightDeleteBtn = document.getElementById('deleteCurrentCardBtn');
        const confirmDeleteBtn = document.getElementById('confirmDeleteCardBtn');
        
        // Handle the top right delete button
        if (topRightDeleteBtn) {
            topRightDeleteBtn.addEventListener('click', () => this.showDeleteConfirmation());
        }
        
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', () => this.deleteCurrentCard());
        }
    }
    
    showDeleteConfirmation() {
        if (!this.currentCard) return;
        
        // Display the card question in the confirmation modal
        const questionEl = document.getElementById('deleteCardQuestion');
        if (questionEl) {
            questionEl.textContent = this.currentCard.question;
        }
        
        // Reset status message
        const statusEl = document.getElementById('deleteCardStatus');
        if (statusEl) {
            statusEl.innerHTML = '';
        }
        
        // Show the modal
        this.deleteCardModal.show();
    }
    
    async deleteCurrentCard() {
        if (!this.currentCard) return;
        
        const cardId = this.currentCard.id;
        const button = document.getElementById('confirmDeleteCardBtn');
        const statusEl = document.getElementById('deleteCardStatus');
        
        // Show loading state
        if (button) {
            const normalState = button.querySelector('.normal-state');
            const loadingState = button.querySelector('.loading-state');
            if (normalState && loadingState) {
                button.disabled = true;
                normalState.classList.add('d-none');
                loadingState.classList.remove('d-none');
            }
        }
        
        try {
            const response = await fetch(`/flashcard/delete/${cardId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete flashcard');
            }
            
            const data = await response.json();
            
            // Remove the card from our array
            const index = this.flashcards.findIndex(card => card.id === cardId);
            if (index !== -1) {
                this.flashcards.splice(index, 1);
                this.totalDueCards = this.flashcards.length;
                
                // Update counter
                this.updateCardCounter();
                
                // Show success message
                if (statusEl) {
                    statusEl.innerHTML = `
                        <div class="alert alert-success mt-2">
                            <i class="bi bi-check-circle me-2"></i>Flashcard deleted successfully!
                        </div>
                    `;
                }
                
                // Close the modal after a short delay and move to next card
                setTimeout(() => {
                    this.deleteCardModal.hide();
                    
                    // If we deleted the last card, show completion state
                    if (this.flashcards.length === 0) {
                        this.ui.showCompletionScreen(this.deckId, this.score, this.totalDueCards, this.studyMode, 0);
                    } else {
                        // If we deleted the current card, we need to show a new one
                        // Make sure we don't go out of bounds
                        this.currentCardIndex = Math.min(this.currentCardIndex, this.flashcards.length - 1);
                        this.moveToNextCard();
                    }
                }, 1000);
            }
        } catch (error) {
            console.error('Error deleting flashcard:', error);
            
            // Show error message
            if (statusEl) {
                statusEl.innerHTML = `
                    <div class="alert alert-danger mt-2">
                        <i class="bi bi-exclamation-triangle me-2"></i>Error: Failed to delete flashcard
                    </div>
                `;
            }
        } finally {
            // Reset button state
            if (button) {
                const normalState = button.querySelector('.normal-state');
                const loadingState = button.querySelector('.loading-state');
                if (normalState && loadingState) {
                    button.disabled = false;
                    normalState.classList.remove('d-none');
                    loadingState.classList.add('d-none');
                }
            }
        }
    }

    /**
     * Show explanation for the current flashcard using the modal
     */
    showExplanation() {
        if (!this.currentCard) return;
        
        const flashcardId = this.currentCard.id;
        try {
            // Ensure the current card is accessible to the UI manager
            this.ui.showExplanationModal(flashcardId);
        } catch (e) {
            console.error('Error showing explanation:', e);
            // Fallback to simple alert with correct answer
            alert(`An error occurred showing the explanation.\n\nCorrect answer: ${this.currentCard.correct_answer}`);
        }
    }
}
