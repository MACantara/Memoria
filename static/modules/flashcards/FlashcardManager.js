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
        this.isSegmentTransition = false; // Track segment transition state
        this.currentCard = null;  // Store the current card data
        this.totalPages = 0;  // Total pages for pagination
        this.currentPage = 0;  // Current page for pagination
        this.cardsPerSegment = 25;  // Default cards per segment
        
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
            // Load all flashcards at once
            await this.loadAllFlashcards();
            
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

    async loadAllFlashcards() {
        try {
            if (this.isLoading) return;
            
            this.isLoading = true;
            
            // Build the URL for loading cards with pagination
            const url = new URL(`/deck/study/${this.deckId}`, window.location.origin);
            
            // Add query parameter for due only
            if (this.studyMode) {
                url.searchParams.append('due_only', 'true');
            }
            
            // Add pagination parameters - load one segment (25 cards) at a time
            url.searchParams.append('page', '1');
            url.searchParams.append('per_page', '25');
            
            console.log(`Loading first segment of flashcards from: ${url}`);
            
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
            this.totalPages = data.pagination.total_pages;
            this.currentPage = 1;
            this.cardsPerSegment = data.pagination.per_page || 25;
            
            console.log(`Successfully loaded segment 1/${this.totalPages} with ${this.flashcards.length} flashcards out of ${data.total} total`);
            
            // Store the total count - don't override it with just first batch size
            if (data.total !== this.totalDueCards) {
                console.log(`Updating total from ${this.totalDueCards} to ${data.total}`);
                this.totalDueCards = data.total;
                
                // Update the counter display with the correct total
                const remainingCountElement = document.getElementById('remainingCount');
                if (remainingCountElement) {
                    remainingCountElement.textContent = this.totalDueCards;
                }
            }
            
            // Dispatch event to indicate first batch loaded
            this.dispatchEvent('firstBatchLoaded');
            
        } catch (error) {
            console.error("Error loading flashcards:", error);
            this.ui.showLoadingError(error.message);
        } finally {
            this.isLoading = false;
        }
    }

    async loadNextSegment() {
        try {
            if (this.isLoading) return false;
            
            // Check if we have more pages to load
            if (this.currentPage >= this.totalPages) {
                console.log("No more segments to load");
                return false;
            }
            
            this.isLoading = true;
            this.isSegmentTransition = true; // Set flag to indicate we're in a segment transition
            console.log(`Starting to load segment ${this.currentPage + 1}/${this.totalPages}`);
            
            // Show loading message between segments
            this.ui.showLoadingMessage(`Loading next segment (${this.currentPage + 1}/${this.totalPages})...`);
            
            // Build the URL for loading the next segment
            const url = new URL(`/deck/study/${this.deckId}`, window.location.origin);
            
            // Add query parameter for due only
            if (this.studyMode) {
                url.searchParams.append('due_only', 'true');
            }
            
            const nextPage = this.currentPage + 1;
            url.searchParams.append('page', nextPage.toString());
            url.searchParams.append('per_page', this.cardsPerSegment.toString());
            
            console.log(`Loading segment ${nextPage}/${this.totalPages} from URL:`, url.toString());
            
            // Ensure this is treated as an AJAX request to prevent page navigation
            try {
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json'
                    },
                    // Prevent browser from navigating to the result
                    mode: 'same-origin',
                    credentials: 'same-origin'
                });
                
                console.log(`Received response for segment ${nextPage}, status:`, response.status);
                
                if (!response.ok) {
                    console.error(`Server returned error ${response.status}`);
                    throw new Error(`Failed to load segment ${nextPage}: ${response.status}`);
                }
                
                const data = await response.json();
                console.log(`Successfully parsed JSON for segment ${nextPage}`);
                
                // Verify we got the expected data structure
                if (!data.flashcards || !Array.isArray(data.flashcards)) {
                    console.error("Invalid data structure received:", data);
                    throw new Error('Received invalid data structure from server');
                }
                
                // Append to existing flashcards array
                const newCards = data.flashcards;
                console.log(`Adding ${newCards.length} new cards to existing ${this.flashcards.length} cards`);
                this.flashcards = [...this.flashcards, ...newCards];
                this.currentPage = nextPage;
                
                console.log(`Added ${newCards.length} more cards, total now: ${this.flashcards.length}`);
                
                // Hide the loading message BEFORE finding and rendering the card
                this.ui.hideLoadingMessage(this.isSegmentTransition);
                console.log("Loading message hidden after successful segment load");
                
                // Verify DOM elements are available before trying to render
                this.verifyDomElements();
                
                // IMPORTANT: Find the first card from the new segment and display it
                const segmentStartIndex = (this.currentPage - 1) * this.cardsPerSegment;
                if (segmentStartIndex < this.flashcards.length) {
                    console.log(`Looking for first uncompleted card starting at index ${segmentStartIndex}`);
                    
                    // Find the first uncompleted card in the new segment
                    let nextCardIndex = -1;
                    for (let i = segmentStartIndex; i < this.flashcards.length; i++) {
                        if (!this.completedCards.has(this.flashcards[i].id)) {
                            nextCardIndex = i;
                            break;
                        }
                    }
                    
                    if (nextCardIndex >= 0) {
                        this.currentCardIndex = nextCardIndex;
                        this.currentCard = this.flashcards[nextCardIndex];
                        console.log(`Found first uncompleted card at index ${nextCardIndex}: ID ${this.currentCard.id}`);
                        
                        // Get reference to the card container and set flashcard ID
                        const currentCardElement = document.getElementById('currentFlashcard');
                        if (currentCardElement) {
                            currentCardElement.style.display = 'block';
                            currentCardElement.dataset.flashcardId = this.currentCard.id;
                            console.log(`Set flashcard ID in DOM element: ${this.currentCard.id}`);
                        } else {
                            console.error("Card container element not found!");
                        }
                        
                        // Render the card immediately
                        this.ui.renderCard(this.currentCard);
                        this.updateCardCounter();
                        console.log("First card from new segment rendered!");
                        
                        return true;
                    } else {
                        console.warn("No uncompleted cards found in the new segment");
                        return false;
                    }
                } else {
                    console.warn(`Start index ${segmentStartIndex} is out of bounds (${this.flashcards.length} total cards)`);
                    return false;
                }
                
            } catch (fetchError) {
                console.error("Fetch error during segment loading:", fetchError);
                
                // Always hide the loading message on error
                this.ui.hideLoadingMessage(this.isSegmentTransition);
                console.log("Loading message hidden after fetch error");
                
                throw fetchError;
            }
        } catch (error) {
            console.error("Error loading next segment:", error);
            
            // Always hide the loading message in the outer catch block too
            this.ui.hideLoadingMessage(this.isSegmentTransition);
            console.log("Loading message hidden in outer catch block");
            
            this.ui.showLoadingError(`Failed to load segment: ${error.message}`);
            return false;
        } finally {
            this.isLoading = false;
            this.isSegmentTransition = false; // Reset segment transition flag
            console.log(`Segment loading completed, isLoading set to false, isSegmentTransition reset to false`);
        }
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
        
        // Check if we've completed a segment and need to load more cards
        if (this.currentPage < this.totalPages && 
            this.completedCards.size > 0 && 
            this.completedCards.size % this.cardsPerSegment === 0) {
            
            console.log(`Completed segment ${this.currentPage}. Loading next segment...`);
            
            // Prevent any user interaction during segment loading
            document.body.classList.add('loading-next-segment');
            this.isSegmentTransition = true; // Set transition flag
            
            try {
                // Show segment completion celebration
                this.ui.celebrateSegmentCompletion(this.currentPage, this.totalPages);
                
                // Add small delay to let the celebration show before starting to load
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Load next segment - this is an async operation
                const loadedSuccessfully = await this.loadNextSegment();
                
                // Note: loadNextSegment now handles displaying the first card from the new segment
                // So we don't need to call moveToNextCard() recursively
                
                if (loadedSuccessfully) {
                    console.log("Successfully loaded next segment, card already rendered");
                    // No need to call moveToNextCard() again since loadNextSegment already displayed a card
                    return;
                } else {
                    // If we failed to load, show error and completion screen
                    console.error("Failed to load next segment, showing completion screen");
                    this.checkRemainingDueCards();
                    return;
                }
            } catch (error) {
                console.error("Error during segment transition:", error);
                // Show error message
                this.ui.showLoadingError("Error loading next segment. Please try refreshing the page.");
            } finally {
                // Re-enable user interaction
                document.body.classList.remove('loading-next-segment');
                this.isSegmentTransition = false; // Reset transition flag when complete
            }
        }
        
        // If we reach here, all cards have been completed
        console.log("All cards completed. Showing completion screen.");
        this.checkRemainingDueCards();
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
