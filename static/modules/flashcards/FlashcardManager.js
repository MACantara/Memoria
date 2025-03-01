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

        setTimeout(() => {
            // Mark card as completed if it's now mastered
            const isMastered = parseInt(flashcard.dataset.state) === 2;
            if (isMastered) {
                flashcard.dataset.completed = 'true';
                
                if (this.completedCards.size === this.flashcardsArray.length) {
                    this.ui.showCompletion(this.score, this.flashcardsArray.length);
                    return;
                }
            } else if (!isCorrect) {
                this.moveCardToEnd(flashcard);
            }
            this.findNextCardToShow();
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
        flashcard.dataset.attempted = 'true';
        
        // Find position after unanswered cards but before completed ones
        let insertIndex = this.flashcardsArray.length;
        for (let i = 0; i < this.flashcardsArray.length; i++) {
            if (!this.isCardUnanswered(this.flashcardsArray[i]) && 
                parseInt(this.flashcardsArray[i].dataset.state || 0) !== 2) {
                insertIndex = i;
                break;
            }
        }
        
        this.container.insertBefore(flashcard, this.flashcardsArray[insertIndex]);
        
        // Reset the card's visual state when moving it
        this.resetAnswerFeedback(flashcard);
        
        this.flashcardsArray = Array.from(document.querySelectorAll('.flashcard'));
    }

    findNextCardToShow() {
        // First try to find an unanswered card
        let nextIndex = this.findNextUnansweredCard();
        
        // If no unanswered cards, look for cards that aren't mastered
        if (nextIndex === -1) {
            nextIndex = this.findNextNonMasteredCard();
        }
        
        // If we found a card to show, show it
        if (nextIndex !== -1) {
            this.currentCardIndex = nextIndex;
            
            // Make sure the card is properly reset before showing
            const nextCard = this.flashcardsArray[this.currentCardIndex];
            
            // Only reinitialize if it's been attempted before
            if (nextCard.dataset.attempted === 'true') {
                this.initializeFlashcard(nextCard);
            }
            
            this.ui.showCard(this.currentCardIndex, this.flashcardsArray, this.score);
        } else {
            this.ui.showCompletion(this.score, this.flashcardsArray.length);
        }
    }

    findNextUnansweredCard() {
        for (let i = 0; i < this.flashcardsArray.length; i++) {
            if (this.isCardUnanswered(this.flashcardsArray[i])) {
                return i;
            }
        }
        return -1;
    }

    findNextNonMasteredCard() {
        for (let i = 0; i < this.flashcardsArray.length; i++) {
            // Not mastered (state != 2)
            if (parseInt(this.flashcardsArray[i].dataset.state || 0) !== 2) {
                return i;
            }
        }
        return -1;
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
