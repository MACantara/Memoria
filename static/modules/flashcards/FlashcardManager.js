import { shuffleArray, updateProgress } from '../utils.js';
import { UIManager } from './UIManager.js';

export class FlashcardManager {
    constructor() {
        this.container = document.getElementById('flashcardsContainer');
        this.currentCardIndex = 0;
        this.score = 0;
        this.flashcardsArray = [];
        this.ui = new UIManager();
        this.completedCards = new Set();
    }

    initialize() {
        if (!this.container) return;
        this.flashcardsArray = Array.from(document.querySelectorAll('.flashcard'));
        this.flashcardsArray.forEach(card => this.initializeFlashcard(card));
        
        // Initialize completed cards based on FSRS state
        this.flashcardsArray.forEach(card => {
            // A card is considered completed if its state is "mastered" (2)
            const state = parseInt(card.dataset.state || 0);
            if (state === 2) {  // 2 = mastered
                this.completedCards.add(card.dataset.id);
                this.score++;
            }
        });
        
        // Update the initial score and progress
        this.ui.updateScore(this.score, this.flashcardsArray.length);
        
        if (this.flashcardsArray.length > 0) {
            this.ui.showCard(0, this.flashcardsArray, this.score);
        }
    }

    initializeFlashcard(flashcard) {
        // Reset any previous answer states first
        this.resetAnswerFeedback(flashcard);
        
        const answersForm = flashcard.querySelector('.answer-form');
        const correctAnswer = flashcard.dataset.correct;
        const incorrectAnswers = JSON.parse(flashcard.dataset.incorrect)
            .map(answer => answer.trim().split('**')[0].trim());
        
        const allAnswers = [correctAnswer, ...incorrectAnswers]
            .filter(answer => answer && answer.length > 0)
            .map(answer => answer.replace(/\*\*.*?\*\*/g, '').trim());
        
        shuffleArray(allAnswers);
        this.ui.renderAnswerOptions(flashcard, allAnswers);
        
        // Update to use Bootstrap form-check-input class
        answersForm.querySelectorAll('.form-check-input').forEach(radio => {
            radio.addEventListener('click', () => this.handleAnswer(radio.value, flashcard));
        });
    }

    // Add new helper function to reset visual feedback
    resetAnswerFeedback(flashcard) {
        // Remove any previous feedback alerts
        const existingFeedback = flashcard.querySelector('.alert');
        if (existingFeedback) {
            existingFeedback.remove();
        }
        
        // Reset all answer options to default state
        flashcard.querySelectorAll('.answer-option').forEach(option => {
            option.classList.remove(
                'border-success', 'bg-success-subtle', 
                'border-danger', 'bg-danger-subtle'
            );
        });
        
        // Uncheck all radio buttons
        flashcard.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.checked = false;
        });
    }

    isCardUnanswered(flashcard) {
        // A card is unanswered if it's in the "new" state (0)
        return parseInt(flashcard.dataset.state || 0) === 0;
    }

    async handleAnswer(selectedAnswer, flashcard) {
        const isCorrect = selectedAnswer === flashcard.dataset.correct;
        
        try {
            // Update server-side progress first
            const result = await updateProgress(flashcard.dataset.id, isCorrect);
            
            if (result.success) {
                // Update FSRS specific data
                flashcard.dataset.state = this.getFsrsStateNumber(result.state);
                flashcard.dataset.retrievability = result.retrievability || 0;
                
                // Update the displayed info in the UI
                this.updateCardStatsUI(flashcard, result);
                
                // Recalculate score based on updated FSRS states
                this.recalculateScore();
            }
        } catch (error) {
            console.error("Failed to update progress:", error);
        }
        
        // Add visual feedback using Bootstrap classes
        flashcard.querySelectorAll('.answer-option').forEach(option => {
            const radio = option.querySelector('input[type="radio"]');
            if (radio.value === flashcard.dataset.correct) {
                option.classList.add('border-success', 'bg-success-subtle');
            } else if (radio.checked && !isCorrect) {
                option.classList.add('border-danger', 'bg-danger-subtle');
            }
        });
        
        this.ui.showAnswerFeedback(flashcard, isCorrect);

        // Mark whether this card has been attempted (for resetting later)
        flashcard.dataset.attempted = 'true';

        // Process the card after showing feedback
        setTimeout(() => {
            // Check for mastery - this affects how we count completed cards
            const isMastered = parseInt(flashcard.dataset.state) === 2;
            if (isMastered) {
                flashcard.dataset.completed = 'true';
                
                // Check if all cards are now mastered
                if (this.completedCards.size === this.flashcardsArray.length) {
                    this.ui.showCompletion(this.score, this.flashcardsArray.length);
                    return;
                }
            }
            
            // If answer was incorrect, move the card to the end of the stack
            if (!isCorrect) {
                this.moveCardToEnd(flashcard);
            } 
            
            // Always move to the next card after answering, regardless of correctness
            this.moveToNextCard();
            
        }, 1500);
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
    
    updateCardStatsUI(flashcard, data) {
        // Update last reviewed date
        const lastReviewedEl = flashcard.querySelector('.last-reviewed');
        const stateEl = flashcard.querySelector('.card-state');
        
        // Format date if provided
        if (lastReviewedEl && data.last_reviewed) {
            const date = new Date(data.last_reviewed);
            lastReviewedEl.textContent = date.toLocaleString();
        }
        
        // Update state label if it exists
        if (stateEl && data.state) {
            stateEl.textContent = data.state;
            
            // Remove all state classes
            stateEl.classList.remove('bg-secondary', 'bg-warning', 'bg-success', 'bg-danger');
            
            // Add appropriate class based on state
            switch(data.state) {
                case 'new':
                    stateEl.classList.add('bg-secondary');
                    break;
                case 'learning':
                    stateEl.classList.add('bg-warning');
                    break;
                case 'mastered':
                    stateEl.classList.add('bg-success');
                    break;
                case 'forgotten':
                    stateEl.classList.add('bg-danger');
                    break;
            }
        }
    }
    
    recalculateScore() {
        // Clear the set and recalculate based on current FSRS states
        this.completedCards.clear();
        this.score = 0;
        
        this.flashcardsArray.forEach(card => {
            // State 2 = mastered
            if (parseInt(card.dataset.state || 0) === 2) {
                this.completedCards.add(card.dataset.id);
                this.score++;
            }
        });
        
        this.ui.updateScore(this.score, this.flashcardsArray.length);
    }

    moveCardToEnd(flashcard) {
        // Find the position after all non-mastered cards
        let insertIndex = this.flashcardsArray.length;
        
        // Start from end and find first mastered card
        for (let i = this.flashcardsArray.length - 1; i >= 0; i--) {
            if (parseInt(this.flashcardsArray[i].dataset.state) === 2) {
                insertIndex = i;
            } else {
                break; // Found the last non-mastered card
            }
        }
        
        // Move the flashcard to after all non-mastered cards but before mastered ones
        this.container.insertBefore(flashcard, this.flashcardsArray[insertIndex]);
        
        // Update the array to reflect the new DOM order
        this.flashcardsArray = Array.from(document.querySelectorAll('.flashcard'));
    }

    moveToNextCard() {
        // Determine the next card to show
        // First check current index + 1
        let nextIndex = this.currentCardIndex + 1;
        
        // If we're at the end, start looking from the beginning
        if (nextIndex >= this.flashcardsArray.length) {
            nextIndex = 0;
        }
        
        // If we're back at the starting index, we've gone through all cards
        let startIndex = this.currentCardIndex;
        
        // Keep looking for a non-mastered card
        while (nextIndex !== startIndex) {
            const nextCard = this.flashcardsArray[nextIndex];
            // A card is available to show if it's not mastered (state != 2)
            if (parseInt(nextCard.dataset.state || 0) !== 2) {
                this.currentCardIndex = nextIndex;
                
                // If the card has been attempted, ensure it's properly reset
                if (nextCard.dataset.attempted === 'true') {
                    this.initializeFlashcard(nextCard);
                }
                
                this.ui.showCard(this.currentCardIndex, this.flashcardsArray, this.score);
                return; // Found a card to show
            }
            
            // Try next index
            nextIndex = (nextIndex + 1) % this.flashcardsArray.length;
        }
        
        // If we get here, all cards are mastered or we've gone through the whole deck
        this.ui.showCompletion(this.score, this.flashcardsArray.length);
    }

    showNextCard() {
        if (this.currentCardIndex < this.flashcardsArray.length - 1) {
            this.currentCardIndex++;
            this.ui.showCard(this.currentCardIndex, this.flashcardsArray, this.score);
        }
    }

    showPreviousCard() {
        if (this.currentCardIndex > 0) {
            this.currentCardIndex--;
            this.ui.showCard(this.currentCardIndex, this.flashcardsArray, this.score);
        }
    }

    getCurrentCard() {
        return this.flashcardsArray[this.currentCardIndex];
    }

    handleKeyboardNavigation(key) {
        const currentCard = this.getCurrentCard();
        if (!currentCard) return;

        const answers = Array.from(currentCard.querySelectorAll('.answer-option'));
        
        switch(key) {
            case '1':
            case '2':
            case '3':
            case '4':
                const index = parseInt(key) - 1;
                if (index < answers.length) {
                    const radio = answers[index].querySelector('input[type="radio"]');
                    if (!radio.checked) {
                        radio.checked = true;
                        this.handleAnswer(radio.value, currentCard);
                    }
                }
                break;
            case 'ArrowRight':
                this.showNextCard();
                break;
            case 'ArrowLeft':
                this.showPreviousCard();
                break;
        }
    }
}
