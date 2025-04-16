import { shuffleArray, updateProgress } from '../utils.js';
import { UIManager } from './UIManager.js';
import { NavigationManager } from './NavigationManager.js';
import { EventManager } from './EventManager.js';

export class FlashcardManager {
    constructor() {
        this.container = document.getElementById('flashcardsContainer');
        this.currentCardIndex = 0;
        this.score = 0;  // Track cards completed in current batch
        this.flashcards = [];  // Store flashcard data, not DOM elements
        this.ui = new UIManager();
        this.completedCards = new Set();  // Track all cards completed in this session
        this.totalDueCards = parseInt(document.getElementById('totalFlashcards')?.value || 0);
        this.deckId = document.getElementById('deckId')?.value;
        this.studyMode = document.getElementById('studyMode')?.value === 'due_only';
        this.isLoading = false;
        this.isSegmentTransition = false; // Track segment transition state
        this.currentCard = null;  // Store the current card data
        this.currentBatch = parseInt(document.getElementById('currentBatch')?.value || 1);
        this.cardsPerBatch = 45;  // Each batch loads 45 cards
        this.totalSessionCompleted = 0; // Track total cards completed across all batches
        this.excludedCardIds = []; // Track card IDs to exclude from future batches
        
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
            // Load the first batch of flashcards
            await this.loadFlashcardBatch(this.currentBatch);
            
            // Initialize milestone segments
            this.ui.initializeMilestones(this.totalDueCards, this.cardsPerBatch);
            
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
        this.ui.updateScore(this.score, this.flashcards.length, this.totalSessionCompleted, this.totalDueCards);
        
        // Setup event listeners
        this.events.setupEventListeners();
    }

    async loadFlashcardBatch(batchNumber) {
        try {
            if (this.isLoading) return;
            
            this.isLoading = true;
            
            // Build the URL for loading cards with pagination
            const url = new URL(`/deck/study/${this.deckId}`, window.location.origin);
            
            // Add query parameter for due only
            if (this.studyMode) {
                url.searchParams.append('due_only', 'true');
            }
            
            // Add parameters for this batch
            url.searchParams.append('page', batchNumber.toString());
            url.searchParams.append('per_page', this.cardsPerBatch.toString());
            
            // Add excluded card IDs if there are any
            if (this.excludedCardIds.length > 0) {
                url.searchParams.append('exclude_ids', this.excludedCardIds.join(','));
            }
            
            console.log(`Loading batch ${batchNumber} flashcards from: ${url}`);
            
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
            
            // Store flashcards in the order they were received
            this.flashcards = data.flashcards;
            this.currentBatch = batchNumber;
            
            console.log(`Successfully loaded ${this.flashcards.length} flashcards (batch ${batchNumber}) out of ${data.total} total`);
            
            // Store the total count from server
            if (data.total !== this.totalDueCards) {
                console.log(`Updating total from ${this.totalDueCards} to ${data.total}`);
                this.totalDueCards = data.total;
                
                // Update the counter display with the correct total
                this.updateTotalCountDisplay(this.totalDueCards);
            }
            
            // For first batch, dispatch event 
            if (batchNumber === 1) {
                this.dispatchEvent('firstBatchLoaded');
            }
            
            // Update batch info displays
            const batchSizeElement = document.getElementById('batchSize');
            if (batchSizeElement) {
                batchSizeElement.textContent = this.flashcards.length;
            }
            
            const batchCardCount = document.getElementById('batchCardCount');
            if (batchCardCount) {
                batchCardCount.textContent = this.flashcards.length;
            }
            
            return this.flashcards.length > 0;
            
        } catch (error) {
            console.error(`Error loading flashcard batch ${batchNumber}:`, error);
            this.ui.showLoadingError(error.message);
            return false;
        } finally {
            this.isLoading = false;
        }
    }
    
    updateTotalCountDisplay(totalCount) {
        // Update all elements that display the total count
        const totalCountElement = document.getElementById('totalCount');
        if (totalCountElement) {
            totalCountElement.textContent = totalCount;
        }
        
        const totalDueDisplay = document.getElementById('totalDueDisplay');
        if (totalDueDisplay) {
            totalDueDisplay.textContent = totalCount;
        }
        
        const totalDueCount = document.getElementById('totalDueCount');
        if (totalDueCount) {
            totalDueCount.textContent = totalCount;
        }
        
        // Update metadata field
        const totalFlashcardsField = document.getElementById('totalFlashcards');
        if (totalFlashcardsField) {
            totalFlashcardsField.value = totalCount;
        }
    }

    async loadNextBatch() {
        // Save the current completed card IDs to exclude from future batches
        this.excludedCardIds = Array.from(this.completedCards);
        
        // Increment batch number
        const nextBatch = this.currentBatch + 1;
        
        // Show loading UI
        this.ui.showBatchLoading();
        
        // Reset current state for the new batch
        this.score = 0;
        this.currentCardIndex = 0;
        
        // Load next batch of cards
        const success = await this.loadFlashcardBatch(nextBatch);
        
        if (success && this.flashcards.length > 0) {
            // Hide batch completion screen
            const batchCompletionScreen = document.getElementById('batchCompletionScreen');
            if (batchCompletionScreen) {
                batchCompletionScreen.style.display = 'none';
            }
            
            // Hide loading indicator
            const loadingContainer = document.getElementById('loadingContainer');
            if (loadingContainer) {
                loadingContainer.style.display = 'none';
            }
            
            // Show first card
            this.currentCard = this.flashcards[0];
            const currentCardElement = document.getElementById('currentFlashcard');
            if (currentCardElement) {
                currentCardElement.style.display = 'block';
                // Add the current flashcard ID as a data attribute
                currentCardElement.dataset.flashcardId = this.currentCard.id;
            }
            
            // Update progress display for new batch
            this.ui.resetProgressForNewBatch(this.currentBatch, Math.ceil(this.totalDueCards / this.cardsPerBatch));
            
            // Render the first card
            this.ui.renderCard(this.currentCard);
            this.updateCardCounter();
        } else {
            // No more cards or error loading
            this.ui.showFinalCompletion(this.deckId, this.totalSessionCompleted, this.totalDueCards, this.studyMode);
        }
    }
    
    // Replace loadAllFlashcards with loadFlashcardBatch
    async loadAllFlashcards() {
        return this.loadFlashcardBatch(1);
    }

    updateCardCounter() {
        // Calculate cards left to review in this batch
        const cardsInBatch = this.flashcards.length;
        const remaining = Math.max(0, cardsInBatch - this.score);
        
        // Calculate overall progress
        const totalCompleted = this.totalSessionCompleted + this.score;
        const overallRemaining = Math.max(0, this.totalDueCards - totalCompleted);
        
        // Use getDisplayIndex to get the correct 1-based card number for display
        const currentIndex = this.getDisplayIndex(this.currentCardIndex);
        
        // Update UI manager's counter with correct display index and overall progress
        this.ui.updateCardCounter(
            currentIndex - 1,          // Current card index (0-based)
            cardsInBatch,              // Cards in current batch
            this.score,                // Cards completed in current batch
            remaining,                 // Cards remaining in current batch
            totalCompleted,            // Total cards completed across all batches
            this.totalDueCards,        // Total cards to study overall
            overallRemaining           // Overall remaining cards
        );
        
        // Also update the completed count in the header
        const completedCount = document.getElementById('completedCount');
        if (completedCount) {
            completedCount.textContent = totalCompleted;
        }
        
        // Log counter state for debugging
        console.log(`Batch ${this.currentBatch}: ${this.score}/${cardsInBatch}, Overall: ${totalCompleted}/${this.totalDueCards}`);
    }

    async moveToNextCard() {
        // Debug info
        console.log("Moving to next card. Completed cards:", this.completedCards.size);
        console.log(`Total cards to review: ${this.totalDueCards}, completed: ${this.score}`);
        
        // Find the next uncompleted card in the original order
        let nextCardIndex = -1;
        
        for (let i = 0; i < this.flashcards.length; i++) {
            // Skip the current card and completed cards
            if (i === this.currentCardIndex || this.completedCards.has(this.flashcards[i].id)) {
                continue;
            }
            
            // In "Due Only" mode, skip mastered cards
            if (this.studyMode && parseInt(this.flashcards[i].state) === 2) {
                continue;
            }
            
            // Found the next card
            nextCardIndex = i;
            break;
        }
        
        // If we couldn't find the next card, try again from the start
        if (nextCardIndex === -1) {
            for (let i = 0; i < this.currentCardIndex; i++) {
                if (!this.completedCards.has(this.flashcards[i].id)) {
                    if (!(this.studyMode && parseInt(this.flashcards[i].state) === 2)) {
                        nextCardIndex = i;
                        break;
                    }
                }
            }
        }
        
        // If we found a valid next card
        if (nextCardIndex !== -1) {
            this.currentCardIndex = nextCardIndex;
            this.currentCard = this.flashcards[nextCardIndex];
            const visibleCardIndex = this.getDisplayIndex(nextCardIndex);
            console.log(`Moving to card ${visibleCardIndex}/${this.totalDueCards} with ID ${this.currentCard.id} (state: ${this.currentCard.state}, due: ${this.currentCard.due_date || 'N/A'})`);
            
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
        
        // If we reach here, all cards have been completed
        console.log("All cards completed. Showing completion screen.");
        this.checkRemainingDueCards();
    }

    /**
     * Verify that all required DOM elements exist for rendering cards
     * If not, attempt to recreate the structure
     */
    verifyDomElements() {
        console.log("Verifying DOM elements for card rendering");
        
        const cardElement = document.getElementById('currentFlashcard');
        const questionElement = document.getElementById('questionContainer');
        const answerFormElement = document.getElementById('answerForm');
        
        if (!cardElement || !questionElement || !answerFormElement) {
            console.error("Required DOM elements missing, attempting to recreate structure");
            this.ui.recreateFlashcardStructure();
            
            // Check if recreation was successful
            const hasCard = document.getElementById('currentFlashcard') !== null;
            const hasQuestion = document.getElementById('questionContainer') !== null;
            const hasAnswerForm = document.getElementById('answerForm') !== null;
            
            console.log(`Structure check after recreation: flashcard=${hasCard}, question=${hasQuestion}, answerForm=${hasAnswerForm}`);
        } else {
            console.log("All required DOM elements found");
        }
    }

    async handleAnswer(selectedAnswer) {
        // Prevent multiple submissions while processing
        if (this.isProcessingAnswer) {
            console.log("Already processing an answer, ignoring duplicate submission");
            return;
        }
        
        console.log(`Handling answer: "${selectedAnswer}"`);
        this.isProcessingAnswer = true;
        
        const card = this.currentCard;
        if (!card) {
            console.error("No current card available");
            this.isProcessingAnswer = false;
            return;
        }
        
        const isCorrect = selectedAnswer === card.correct_answer;
        console.log(`Answer is ${isCorrect ? 'correct' : 'incorrect'}`);
        
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
            this.totalSessionCompleted++;
            
            // Debug info
            console.log(`Card ${card.id} completed. Score: ${this.score}/${this.flashcards.length}, Total: ${this.totalSessionCompleted}/${this.totalDueCards}`);
            
            // Update the progress display
            this.ui.updateScore(this.score, this.flashcards.length, this.totalSessionCompleted, this.totalDueCards);
        }
        
        // Show different feedback based on correctness
        if (isCorrect) {
            // For correct answers, show brief feedback then auto-advance
            this.ui.showBriefFeedback(true);
            
            // Set a short timeout to auto-advance
            setTimeout(() => {
                // If all cards in this batch are completed, show batch completion screen
                if (this.score >= this.flashcards.length) {
                    console.log("Batch completed. Showing batch completion screen.");
                    this.showBatchCompletion();
                } else {
                    // Otherwise move to the next card
                    this.moveToNextCard();
                }
            }, 1000); // Show success for 1 second before advancing
        } else {
            // For incorrect answers, show feedback with "Next" button
            this.ui.showAnswerFeedback(false, () => {
                // This callback is triggered when the user clicks "Next"
                
                // If all cards in this batch are completed, show batch completion screen
                if (this.score >= this.flashcards.length) {
                    console.log("Batch completed. Showing batch completion screen.");
                    this.showBatchCompletion();
                } else {
                    // Otherwise move to the next card
                    this.moveToNextCard();
                }
            });
        }
        
        // Reset processing flag
        this.isProcessingAnswer = false;
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

    showBatchCompletion() {
        // Hide the flashcard
        const currentFlashcard = document.getElementById('currentFlashcard');
        if (currentFlashcard) {
            currentFlashcard.style.display = 'none';
        }
        
        // Check if we've completed all cards in the deck
        const allCardsCompleted = this.totalSessionCompleted >= this.totalDueCards;
        
        // If we've completed all cards, show final completion
        if (allCardsCompleted) {
            this.checkRemainingDueCards();
            return;
        }
        
        // Show batch completion screen
        const batchCompletionScreen = document.getElementById('batchCompletionScreen');
        if (batchCompletionScreen) {
            // Update the completion screen data
            const completedBatchCount = document.getElementById('completedBatchCount');
            if (completedBatchCount) {
                completedBatchCount.textContent = this.score;
            }
            
            const sessionCompletedCount = document.getElementById('sessionCompletedCount');
            if (sessionCompletedCount) {
                sessionCompletedCount.textContent = this.totalSessionCompleted;
            }
            
            // Calculate and display overall progress
            const overallProgressBar = document.getElementById('overallProgressBar');
            if (overallProgressBar) {
                const percentComplete = Math.round((this.totalSessionCompleted / this.totalDueCards) * 100);
                overallProgressBar.style.width = `${percentComplete}%`;
                overallProgressBar.setAttribute('aria-valuenow', percentComplete);
                overallProgressBar.textContent = `${percentComplete}%`;
            }
            
            // Enable the next batch button
            const loadNextBatchBtn = document.getElementById('loadNextBatchBtn');
            if (loadNextBatchBtn) {
                loadNextBatchBtn.disabled = false;
                const normalState = loadNextBatchBtn.querySelector('.normal-state');
                const loadingState = loadNextBatchBtn.querySelector('.loading-state');
                if (normalState && loadingState) {
                    normalState.classList.remove('d-none');
                    loadingState.classList.add('d-none');
                }
            }
            
            // Show the completion screen
            batchCompletionScreen.style.display = 'block';
        }
    }

    checkRemainingDueCards() {
        // Hide current flashcard and batch completion screen
        const currentFlashcard = document.getElementById('currentFlashcard');
        if (currentFlashcard) {
            currentFlashcard.style.display = 'none';
        }
        
        const batchCompletionScreen = document.getElementById('batchCompletionScreen');
        if (batchCompletionScreen) {
            batchCompletionScreen.style.display = 'none';
        }
        
        // Get the current study mode
        const isDueOnly = this.studyMode;
        
        // In "Study All" mode, we know we've completed everything, so no need to check server
        if (!isDueOnly) {
            this.ui.showFinalCompletion(this.deckId, this.totalSessionCompleted, this.totalDueCards, isDueOnly, 0);
            return;
        }
        
        // In "Due Only" mode, check if there are more due cards that were added since we started
        fetch(`/deck/api/due-count/${this.deckId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const remainingDueCards = data.due_count - this.totalSessionCompleted;
                    console.log(`Remaining due cards: ${remainingDueCards}`);
                    
                    // Display final completion with information about remaining due cards
                    this.ui.showFinalCompletion(this.deckId, this.totalSessionCompleted, this.totalDueCards, isDueOnly, Math.max(0, remainingDueCards));
                } else {
                    // Error fetching due count, just show normal completion
                    this.ui.showFinalCompletion(this.deckId, this.totalSessionCompleted, this.totalDueCards, isDueOnly, 0);
                }
            })
            .catch(error => {
                console.error("Error checking remaining due cards:", error);
                // Error occurred, just show normal completion
                this.ui.showFinalCompletion(this.deckId, this.totalSessionCompleted, this.totalDueCards, isDueOnly, 0);
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
