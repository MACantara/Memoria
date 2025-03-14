/**
 * NavigationManager - Handles keyboard navigation and shortcuts
 */
export class NavigationManager {
    /**
     * @param {Object} flashcardManager - Reference to the FlashcardManager instance
     */
    constructor(flashcardManager) {
        this.manager = flashcardManager;
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
     * Handle keyboard press events
     * @param {string} key - The key that was pressed
     */
    handleKeyPress(key) {
        // If user has already answered and feedback is showing
        const feedbackContainer = document.querySelector('.feedback-container');
        if (feedbackContainer) {
            // Press any key to continue to next question
            const nextButton = feedbackContainer.querySelector('button');
            if (nextButton) {
                nextButton.click();
                return true;
            }
        } else {
            // If we're in answering mode, numeric keys are handled in EventManager
            if (key >= '1' && key <= '9') {
                return true; // Already handled in EventManager
            }
            
            // Handle answer selection with keyboard
            switch (key.toLowerCase()) {
                // Add other keyboard shortcuts if needed
                case 'n':
                    // Try to skip to the next card
                    this.manager.moveToNextCard();
                    return true;
            }
        }
        
        return false;
    }
    
    /**
     * Visual feedback when trying to advance without selecting an answer
     */
    pulseOptions() {
        const options = document.querySelectorAll('.answer-option');
        options.forEach(option => {
            option.classList.add('pulse-hint');
            setTimeout(() => {
                option.classList.remove('pulse-hint');
            }, 1000);
        });
    }
}
