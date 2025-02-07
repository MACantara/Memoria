import { shuffleArray, updateProgress } from './utils.js';
import { UIManager } from './UIManager.js';

export class FlashcardManager {
    constructor() {
        this.container = document.getElementById('flashcardsContainer');
        this.currentCardIndex = 0;
        this.score = 0;
        this.flashcardsArray = [];
        this.ui = new UIManager();
    }

    initialize() {
        if (!this.container) return;
        this.flashcardsArray = Array.from(document.querySelectorAll('.flashcard'));
        this.flashcardsArray.forEach(card => this.initializeFlashcard(card));
        if (this.flashcardsArray.length > 0) {
            this.ui.showCard(0, this.flashcardsArray, this.score);
        }
    }

    initializeFlashcard(flashcard) {
        const answersForm = flashcard.querySelector('.answer-form');
        const correctAnswer = flashcard.dataset.correct;
        const incorrectAnswers = JSON.parse(flashcard.dataset.incorrect)
            .map(answer => answer.trim().split('**')[0].trim());
        
        const allAnswers = [correctAnswer, ...incorrectAnswers]
            .filter(answer => answer && answer.length > 0)
            .map(answer => answer.replace(/\*\*.*?\*\*/g, '').trim());
        
        shuffleArray(allAnswers);
        this.ui.renderAnswerOptions(flashcard, allAnswers);
        
        answersForm.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.addEventListener('click', () => this.handleAnswer(radio.value, flashcard));
        });
    }

    isCardUnanswered(flashcard) {
        return !flashcard.dataset.completed && !flashcard.dataset.attempted;
    }

    async handleAnswer(selectedAnswer, flashcard) {
        const isCorrect = selectedAnswer === flashcard.dataset.correct;
        await updateProgress(flashcard.dataset.id, isCorrect);
        
        this.ui.showAnswerFeedback(flashcard, isCorrect);

        setTimeout(() => {
            if (isCorrect) {
                this.score++;
                flashcard.dataset.completed = 'true';
                this.ui.updateScore(this.score);
                
                if (this.score === this.flashcardsArray.length) {
                    this.ui.showCompletion(this.score, this.flashcardsArray.length);
                    return;
                }
            } else {
                this.moveCardToEnd(flashcard);
            }
            this.findNextCardToShow();
        }, 1500);
    }

    moveCardToEnd(flashcard) {
        flashcard.dataset.attempted = 'true';
        
        // Find position after unanswered cards but before completed ones
        let insertIndex = this.flashcardsArray.length;
        for (let i = 0; i < this.flashcardsArray.length; i++) {
            if (!this.isCardUnanswered(this.flashcardsArray[i]) && 
                !this.flashcardsArray[i].dataset.completed) {
                insertIndex = i;
                break;
            }
        }
        
        this.container.insertBefore(flashcard, this.flashcardsArray[insertIndex]);
        flashcard.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.checked = false;
        });
        this.flashcardsArray = Array.from(document.querySelectorAll('.flashcard'));
    }

    findNextCardToShow() {
        // First try to find an unanswered card
        let nextIndex = this.findNextUnansweredCard();
        
        // If no unanswered cards, look for incorrect cards
        if (nextIndex === -1) {
            nextIndex = this.findNextIncorrectCard();
        }
        
        // If we found a card to show, show it
        if (nextIndex !== -1) {
            this.currentCardIndex = nextIndex;
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

    findNextIncorrectCard() {
        for (let i = 0; i < this.flashcardsArray.length; i++) {
            if (!this.flashcardsArray[i].dataset.completed) {
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
