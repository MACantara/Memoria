import { shuffleArray, updateProgress } from '../utils.js';
import { UIManager } from './UIManager.js';

export class FlashcardManager {
    constructor() {
        this.container = document.getElementById('flashcardsContainer');
        this.currentCardIndex = 0;
        this.score = 0;  // This will now track cards completed in this session
        this.flashcardsArray = [];
        this.ui = new UIManager();
        this.completedCards = new Set();  // Track cards completed in this session
        this.totalDueCards = 0;  // Track how many due cards we started with
        this.statusBadge = document.getElementById('statusBadge');
    }

    initialize() {
        if (!this.container) return;
        this.flashcardsArray = Array.from(document.querySelectorAll('.flashcard'));
        this.flashcardsArray.forEach(card => this.initializeFlashcard(card));
        
        // Count due cards - these are cards that aren't already mastered (state !== 2)
        this.totalDueCards = this.flashcardsArray.filter(card => {
            const state = parseInt(card.dataset.state || 0);
            return state !== 2;  // Not mastered
        }).length;
        
        // Initialize with 0 completed cards
        this.score = 0;
        
        // Update the initial score and progress display
        this.ui.updateScore(this.score, this.totalDueCards);
        
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

        // Mark this card as completed in this session (regardless of correctness)
        if (!this.completedCards.has(flashcard.dataset.id)) {
            this.completedCards.add(flashcard.dataset.id);
            this.score++;
            
            // Update the progress display
            this.ui.updateScore(this.score, this.totalDueCards);
        }

        // Mark whether this card has been attempted (for resetting later)
        flashcard.dataset.attempted = 'true';

        // Process the card after showing feedback
        setTimeout(() => {
            // Check if all due cards have been completed in this session
            if (this.score >= this.totalDueCards) {
                this.ui.showCompletion(this.score, this.totalDueCards);
                return;
            }
            
            // If answer was incorrect, move card to end for review
            if (!isCorrect) {
                this.moveCardToEnd(flashcard);
            }
            
            // Always move to the next card after answering
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
            
            // Update the prominent status badge using the UI manager
            this.ui.updateStatusBadge(this.getFsrsStateNumber(data.state));
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
        // Find position after all non-mastered, non-completed cards
        let insertIndex = this.flashcardsArray.length;
        
        // Try to find a position before mastered cards and after uncompleted cards
        for (let i = 0; i < this.flashcardsArray.length; i++) {
            const card = this.flashcardsArray[i];
            
            // If we find a mastered card or already completed card, insert before it
            // This ensures incorrectly answered cards go after fresh cards but before finished ones
            if (parseInt(card.dataset.state) === 2 || this.completedCards.has(card.dataset.id)) {
                insertIndex = i;
                break;
            }
        }
        
        // Move the flashcard to the determined position
        this.container.insertBefore(flashcard, this.flashcardsArray[insertIndex]);
        
        // Update the array to reflect the new DOM order
        this.flashcardsArray = Array.from(document.querySelectorAll('.flashcard'));
    }

    moveToNextCard() {
        // First look for cards that haven't been completed in this session
        for (let i = 0; i < this.flashcardsArray.length; i++) {
            // Skip current card
            if (i === this.currentCardIndex) continue;
            
            const card = this.flashcardsArray[i];
            
            // If card is not mastered and not completed in this session, show it
            if (!this.completedCards.has(card.dataset.id) && 
                parseInt(card.dataset.state || 0) !== 2) {
                
                this.currentCardIndex = i;
                
                // Reset card if it's been attempted before
                if (card.dataset.attempted === 'true') {
                    this.initializeFlashcard(card);
                }
                
                this.ui.showCard(this.currentCardIndex, this.flashcardsArray, this.score);
                return;
            }
        }
        
        // If all cards are either mastered or completed in this session, show completion
        this.ui.showCompletion(this.score, this.totalDueCards);
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
