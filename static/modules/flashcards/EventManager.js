/**
 * EventManager - Handles DOM events and delegates to the appropriate manager
 */
export class EventManager {
    /**
     * @param {Object} flashcardManager - Reference to the FlashcardManager instance
     * @param {Object} uiManager - Reference to the UIManager instance
     */
    constructor(flashcardManager, uiManager) {
        this.manager = flashcardManager;
        this.ui = uiManager;
        this.answerForm = document.getElementById('answerForm');
        this.flashcardContainer = document.getElementById('flashcardsContainer');
    }
    
    /**
     * Set up all event listeners needed for the flashcard UI
     */
    setupEventListeners() {
        // Set up answer form submission (delegation)
        if (this.answerForm) {
            // Add event listener to the form to prevent default submission
            this.answerForm.addEventListener('submit', (e) => {
                console.log('Preventing form submission');
                e.preventDefault();
                e.stopPropagation();
                return false;
            });
            
            // Listen for click events on answer options
            this.answerForm.addEventListener('click', (e) => {
                // Prevent any default behavior that might cause form submission
                e.preventDefault();
                
                const answerOption = e.target.closest('.answer-option');
                if (answerOption) {
                    const radio = answerOption.querySelector('input[type="radio"]');
                    if (radio && !radio.checked) {
                        radio.checked = true;
                        
                        // Stop event propagation to prevent bubbling
                        e.stopPropagation();
                        
                        // Notify FlashcardManager about the answer
                        this.manager.handleAnswer(radio.value);
                    }
                }
                
                // Return false to prevent any other handling
                return false;
            });
        }
        
        // Set up keyboard navigation events
        document.addEventListener('keydown', this.handleKeyboardShortcut.bind(this));
        
        // Set up click handler for edit button in header
        const editButton = document.getElementById('editCurrentCardBtn');
        if (editButton) {
            editButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.editCurrentCard();
            });
        }
        
        // Handle swipe gestures for mobile (optional)
        this.setupMobileGestures();
    }
    
    /**
     * Handle keyboard shortcuts
     * @param {KeyboardEvent} e - The keyboard event
     */
    handleKeyboardShortcut(e) {
        // Don't interfere with input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        // Check if we're in answer selection mode (not after answer is shown)
        const feedbackContainer = document.querySelector('.feedback-container');
        
        // NEW: Check if any answer is already selected
        const anyAnswerSelected = document.querySelector('.answer-option.selected');
        
        if (!feedbackContainer && !anyAnswerSelected) {
            // Handle numeric keys 1-9 for answer selection ONLY when no answer is selected yet
            if (e.key >= '1' && e.key <= '9') {
                const index = parseInt(e.key) - 1;
                const answerOptions = document.querySelectorAll('.answer-option');
                
                if (index < answerOptions.length) {
                    const option = answerOptions[index];
                    const radio = option.querySelector('input[type="radio"]');
                    
                    if (radio) {
                        // Update visual selection first
                        this.updateSelectionState(option);
                        
                        // Then handle the answer
                        radio.checked = true;
                        this.manager.handleAnswer(radio.value);
                        
                        // Prevent default behavior (page scrolling)
                        e.preventDefault();
                        e.stopPropagation();
                        return false;
                    }
                }
            }
        } else if (feedbackContainer || anyAnswerSelected) {
            // In feedback mode OR when an answer is already selected
            if (e.key === 'x' || e.key === 'X') {
                // Add 'X' shortcut for showing explanation
                const explainButton = document.getElementById('explainFlashcardBtn');
                if (explainButton && !explainButton.disabled) {
                    explainButton.click();
                    e.preventDefault();
                    return;
                }
            } else if (e.key !== 'e' && e.key !== 'E' && e.key !== 'd' && e.key !== 'D' && e.key !== 'Delete') { 
                // For keys that aren't edit/delete shortcuts, try to advance to next card
                // if we're showing feedback or have an answer selected
                
                // Make sure we're not focused on the Explain button
                const explainButton = document.getElementById('explainFlashcardBtn');
                if (document.activeElement !== explainButton) {
                    // Only click the specific next button, not any button
                    const nextButton = document.getElementById('nextQuestionBtn');
                    if (nextButton) {
                        nextButton.click();
                        e.preventDefault();
                        return;
                    }
                    
                    // If the Next button isn't present but we've already selected an answer,
                    // we might need to trigger the initial answer submission
                    if (anyAnswerSelected && !feedbackContainer) {
                        // The answer is selected but not yet submitted - let's confirm it
                        const radio = anyAnswerSelected.querySelector('input[type="radio"]');
                        if (radio && !radio.disabled) {
                            this.manager.handleAnswer(radio.value);
                            e.preventDefault();
                            return;
                        }
                    }
                }
            }
        }
        
        // Add 'E' shortcut for edit functionality - available at any time
        if ((e.key === 'e' || e.key === 'E') && !e.ctrlKey && !e.altKey && !e.metaKey) {
            this.editCurrentCard();
            e.preventDefault();
        }

        // Add 'Delete' or 'D' shortcut for delete functionality
        if ((e.key === 'Delete' || e.key.toLowerCase() === 'd') && !e.ctrlKey && !e.altKey && !e.metaKey) {
            const deleteBtn = document.getElementById('deleteCurrentCardBtn');
            if (deleteBtn) {
                deleteBtn.click();
                e.preventDefault();
            }
        }
    }
    
    /**
     * Edit the current flashcard
     */
    editCurrentCard() {
        // Check if modal is already open to prevent multiple instances
        const modalElement = document.getElementById('editFlashcardModal');
        if (modalElement && modalElement.classList.contains('show')) {
            console.log('Edit modal is already open');
            return;
        }
        
        if (this.manager && this.manager.currentCard) {
            const flashcardId = this.manager.currentCard.id;
            if (flashcardId) {
                this.manager.showEditModal(flashcardId);
            }
        }
    }
    
    /**
     * Update the visual selection state for an answer option
     * @param {HTMLElement} selectedOption - The option to mark as selected
     */
    updateSelectionState(selectedOption) {
        if (!selectedOption) return;
        
        const answerContainer = selectedOption.closest('div').parentElement;
        if (!answerContainer) return;
        
        // Get the current theme
        const isDarkTheme = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        
        // First clear all selections
        const allOptions = answerContainer.querySelectorAll('.answer-option');
        allOptions.forEach(option => {
            option.classList.remove('selected', 'border-primary');
            // Remove theme-specific classes
            const optionLabel = option.querySelector('label');
            if (optionLabel) {
                optionLabel.classList.remove('bg-light', 'bg-dark-subtle');
            }
            const innerDot = option.querySelector('.inner-circle');
            if (innerDot) innerDot.classList.add('d-none');
        });
        
        // Then add selection to the chosen option
        selectedOption.classList.add('selected', 'border-primary');
        
        // Add the appropriate theme-specific class
        const label = selectedOption.querySelector('label');
        if (label) {
            label.classList.add(isDarkTheme ? 'bg-dark-subtle' : 'bg-light');
        }
        
        const innerCircle = selectedOption.querySelector('.inner-circle');
        if (innerCircle) innerCircle.classList.remove('d-none');
    }
    
    /**
     * Set up touch swipe gestures for mobile navigation
     */
    setupMobileGestures() {
        if (!this.flashcardContainer) return;
        
        let touchStartX = 0;
        let touchEndX = 0;
        
        this.flashcardContainer.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        });
        
        this.flashcardContainer.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            this.handleSwipe(touchStartX, touchEndX);
        });
    }
    
    /**
     * Handle swipe gesture
     * @param {number} startX - Touch start X position
     * @param {number} endX - Touch end X position
     */
    handleSwipe(startX, endX) {
        const threshold = 100; // Minimum swipe distance
        
        // Handle swipe left (next card)
        if (startX - endX > threshold) {
            // Only proceed if we're in an answer feedback state with a "Next" button
            const nextButton = document.querySelector('.feedback-container .btn');
            if (nextButton) {
                nextButton.click();
            }
        }
        
        // Handle swipe right (previous card) - currently disabled as not needed
        // if (endX - startX > threshold) {
        //     this.manager.showPreviousCard();
        // }
    }
    
    /**
     * Remove all event listeners (for cleanup)
     */
    cleanup() {
        // If needed, we can implement this to remove event listeners
        // when the flashcard component is destroyed
    }
}
