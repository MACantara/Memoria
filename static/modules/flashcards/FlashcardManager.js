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
        
        // Debug info to help diagnose issues
        console.log(`Found ${this.flashcardsArray.length} flashcards in DOM`);
        
        this.flashcardsArray.forEach(card => this.initializeFlashcard(card));
        
        // Count due cards - these are cards that aren't already mastered (state !== 2)
        // IMPORTANT FIX: When in "Study All" mode, consider all cards as due regardless of state
        const isDueOnly = new URLSearchParams(window.location.search).get('due_only') === 'true';
        
        // In "Study All" mode, all cards are considered due for review
        this.totalDueCards = isDueOnly ? 
            this.flashcardsArray.filter(card => parseInt(card.dataset.state || 0) !== 2).length :
            this.flashcardsArray.length;
        
        console.log(`Total due cards: ${this.totalDueCards} out of ${this.flashcardsArray.length}`);
        
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
            .map(answer => answer.trim());
        
        // Simplify answer preprocessing - no longer remove markdown formatting
        const allAnswers = [correctAnswer, ...incorrectAnswers]
            .filter(answer => answer && answer.length > 0);
        
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
        // Prevent multiple submissions while processing
        if (this.isProcessingAnswer) return;
        this.isProcessingAnswer = true;
        
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
        
        // Mark this card as completed in this session (regardless of correctness)
        if (!this.completedCards.has(flashcard.dataset.id)) {
            this.completedCards.add(flashcard.dataset.id);
            this.score++;
            
            // Debug info
            console.log(`Card ${flashcard.dataset.id} completed. Score: ${this.score}/${this.totalDueCards}`);
            
            // Update the progress display
            this.ui.updateScore(this.score, this.totalDueCards);
        }
        
        // Mark whether this card has been attempted (for resetting later)
        flashcard.dataset.attempted = 'true';
        
        // MODIFIED BEHAVIOR: Show different feedback based on correctness
        if (isCorrect) {
            // For correct answers, show brief feedback then auto-advance
            this.ui.showBriefFeedback(flashcard, true);
            
            // Set a short timeout to auto-advance
            setTimeout(() => {
                // If all cards are completed, show completion screen
                if (this.completedCards.size >= this.totalDueCards) {
                    console.log("All cards completed. Showing completion screen.");
                    this.ui.showCompletion(this.score, this.totalDueCards);
                } else {
                    // Otherwise move to the next card
                    this.moveToNextCard();
                }
            }, 1000); // Show success for 1 second before advancing
        } else {
            // For incorrect answers, show feedback with "Next" button
            this.ui.showAnswerFeedback(flashcard, false, () => {
                // This callback is triggered when the user clicks "Next"
                this.moveCardToEnd(flashcard);
                
                // If all cards are completed, show completion screen
                if (this.completedCards.size >= this.totalDueCards) {
                    console.log("All cards completed. Showing completion screen.");
                    this.ui.showCompletion(this.score, this.totalDueCards);
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
        // Debug info
        console.log("Moving to next card. Completed cards:", this.completedCards.size);
        
        // FIX: In "Study All" mode, we should show all cards regardless of state
        const isDueOnly = new URLSearchParams(window.location.search).get('due_only') === 'true';
        
        // First look for cards that haven't been completed in this session
        for (let i = 0; i < this.flashcardsArray.length; i++) {
            // Skip current card
            if (i === this.currentCardIndex) continue;
            
            const card = this.flashcardsArray[i];
            const cardState = parseInt(card.dataset.state || 0);
            
            // In "Study All" mode, show any card that hasn't been completed in this session
            // In "Due Only" mode, only show cards that aren't mastered and haven't been completed
            if (!this.completedCards.has(card.dataset.id) && 
                (isDueOnly ? cardState !== 2 : true)) {
                
                this.currentCardIndex = i;
                console.log(`Moving to card ${i+1}/${this.flashcardsArray.length} with ID ${card.dataset.id}`);
                
                // Reset card if it's been attempted before
                if (card.dataset.attempted === 'true') {
                    this.initializeFlashcard(card);
                }
                
                this.ui.showCard(this.currentCardIndex, this.flashcardsArray, this.score);
                return;
            }
        }
        
        // If we reach here, all cards have been completed in this session
        console.log("No more cards to show. All completed.");
        
        // Make sure score reflects completion
        this.score = this.totalDueCards;
        this.ui.updateScore(this.score, this.totalDueCards);
        
        // Show completion screen
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
