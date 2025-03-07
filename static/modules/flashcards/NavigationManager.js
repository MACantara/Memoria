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
        
        // Handle keyboard shortcuts based on context
        switch (key) {
            case 'Enter':
            case ' ': // Space
                // If viewing a card but no answer selected, pulse the options to indicate need to select
                if (isReviewingCard && !hasSelectedAnswer && !hasAnswerFeedback) {
                    this.pulseOptions();
                    return;
                }
                break;
                
            // Number keys for quick answer selection (1-4)
            case '1':
            case '2':
            case '3':
            case '4':
                // Only work if viewing card options and not already in feedback state
                if (isReviewingCard && !hasAnswerFeedback) {
                    const optionIndex = parseInt(key) - 1;
                    const options = document.querySelectorAll('.answer-option');
                    
                    if (optionIndex >= 0 && optionIndex < options.length) {
                        console.log(`Selecting option ${optionIndex + 1}`);
                        const radioInput = options[optionIndex].querySelector('input[type="radio"]');
                        if (radioInput) {
                            // Check the radio input
                            radioInput.checked = true;
                            
                            // Get the answer value and submit it directly to the manager
                            const answerValue = radioInput.value;
                            if (this.manager) {
                                this.manager.handleAnswer(answerValue);
                            } else if (window.flashcardManager) {
                                // Fallback to window.flashcardManager if this.manager is not available
                                window.flashcardManager.handleAnswer(answerValue);
                            }
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
