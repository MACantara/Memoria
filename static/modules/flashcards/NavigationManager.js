/**
 * NavigationManager - Handles navigation through flashcards
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
     * Handle keyboard navigation
     * @param {string} key - The pressed key
     */
    handleKeyPress(key) {
        // Get current state
        const isReviewingCard = !!document.querySelector('.answer-option');
        const hasSelectedAnswer = !!document.querySelector('input[type="radio"]:checked');
        const nextButton = document.querySelector('.feedback-container .btn');
        const hasAnswerFeedback = !!document.querySelector('.feedback-container');
        
        console.log(`Key pressed: ${key}, isReviewing: ${isReviewingCard}, hasSelected: ${hasSelectedAnswer}, hasNext: ${!!nextButton}`);
        
        // Handle Next Question - if we have answer feedback showing with next button, ANY key advances
        if (hasAnswerFeedback && nextButton) {
            // Proceed to next question when any key is pressed after seeing feedback
            nextButton.click();
            return;
        }
        
        // Handle keyboard shortcuts based on context - only if we're not in answer feedback mode
        switch (key) {
            case 'Enter':
            case ' ': // Space
                // If viewing a card but no answer selected, pulse the options to indicate need to select
                if (isReviewingCard && !hasSelectedAnswer && !hasAnswerFeedback) {
                    this.pulseOptions();
                    return;
                }
                break;
                
            case 'ArrowRight':
            case 'n':
            case 'N':
                // These keys are now redundant for next question (any key works in feedback state)
                // But we keep them for consistency in the UI hints
                break;
                
            // Number keys for quick answer selection (1-4)
            case '1':
            case '2':
            case '3':
            case '4':
                // Only work if viewing options and haven't already selected
                if (isReviewingCard && !hasSelectedAnswer && !hasAnswerFeedback) {
                    const optionIndex = parseInt(key) - 1;
                    const options = document.querySelectorAll('.answer-option');
                    
                    if (optionIndex >= 0 && optionIndex < options.length) {
                        console.log(`Selecting option ${optionIndex + 1}`);
                        const radioInput = options[optionIndex].querySelector('input[type="radio"]');
                        if (radioInput) {
                            radioInput.checked = true;
                            // Trigger a click event on the answer option to activate the handler
                            options[optionIndex].click();
                        }
                    }
                }
                break;
        }
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
