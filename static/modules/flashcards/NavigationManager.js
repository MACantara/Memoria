/**
 * NavigationManager - Handles keyboard navigation and movement between flashcards
 */
export class NavigationManager {
    /**
     * @param {Object} flashcardManager - Reference to the FlashcardManager instance
     */
    constructor(flashcardManager) {
        this.manager = flashcardManager;
        this.keybindings = {
            // Number keys 1-4 for answer selection
            '1': this.selectAnswerByNumber.bind(this, 0),
            '2': this.selectAnswerByNumber.bind(this, 1),
            '3': this.selectAnswerByNumber.bind(this, 2),
            '4': this.selectAnswerByNumber.bind(this, 3),
            
            // Space for advancing
            ' ': this.advanceCard.bind(this),
            
            // Arrow keys for navigation (future enhancement)
            'ArrowRight': this.advanceCard.bind(this),
        };
    }

    initialize() {
        if (!this.prevButton || !this.nextButton) return;

        this.prevButton.addEventListener('click', () => {
            this.flashcardManager.showPreviousCard();
        });

        this.nextButton.addEventListener('click', () => {
            this.flashcardManager.showNextCard();
        });

        // Initialize keyboard navigation
        document.addEventListener('keydown', (e) => {
            this.handleKeyPress(e.key);
        });
    }

    /**
     * Handle keyboard navigation
     * @param {string} key - The key that was pressed
     */
    handleKeyPress(key) {
        if (this.keybindings[key]) {
            this.keybindings[key]();
        }
    }
    
    /**
     * Select an answer option by its number (1-4)
     * @param {number} index - The zero-based index of the answer to select
     */
    selectAnswerByNumber(index) {
        if (!this.manager.currentCard) return;
        
        // Find all answer options
        const answerForm = document.getElementById('answerForm');
        if (!answerForm) return;
        
        const answerOptions = answerForm.querySelectorAll('.answer-option');
        if (index >= 0 && index < answerOptions.length) {
            // Simulate a click on the answer option
            answerOptions[index].click();
        }
    }
    
    /**
     * Advance to the next card or trigger the Next button if present
     */
    advanceCard() {
        if (!this.manager.currentCard) return;
        
        // Check if we have a next button (for incorrect answers)
        const nextButton = document.querySelector('.feedback-container .btn');
        if (nextButton) {
            nextButton.click();
            return;
        }
        
        // Check if the current card has been answered before allowing advancement
        const currentCardId = this.manager.currentCard.id;
        if (this.manager.completedCards.has(currentCardId)) {
            // If current card is complete, we can safely move to the next card
            if (this.manager.completedCards.size < this.manager.totalDueCards) {
                this.manager.moveToNextCard();
            }
        } else {
            // Card hasn't been answered yet - show a subtle hint
            const answerForm = document.getElementById('answerForm');
            if (answerForm) {
                // Add a subtle pulse animation to hint that user should answer
                answerForm.classList.add('pulse-hint');
                
                // Remove the animation class after it completes
                setTimeout(() => {
                    answerForm.classList.remove('pulse-hint');
                }, 1000);
            }
        }
    }
}
