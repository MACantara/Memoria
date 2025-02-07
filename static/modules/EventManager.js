export class EventManager {
    constructor(flashcardManager, navigationManager) {
        this.flashcardManager = flashcardManager;
        this.navigationManager = navigationManager;
    }

    initialize() {
        // Initialize all event listeners
        this.initializeDOMContentLoaded();
        this.initializeKeyboardEvents();
        this.initializeAnswerEvents();
    }

    initializeDOMContentLoaded() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.flashcardManager.initialize();
                this.navigationManager.initialize();
            });
        } else {
            this.flashcardManager.initialize();
            this.navigationManager.initialize();
        }
    }

    initializeKeyboardEvents() {
        document.addEventListener('keydown', (e) => {
            // Prevent default arrow key scrolling
            if (['ArrowLeft', 'ArrowRight'].includes(e.key)) {
                e.preventDefault();
            }
            this.flashcardManager.handleKeyboardNavigation(e.key);
        });
    }

    initializeAnswerEvents() {
        document.addEventListener('click', (e) => {
            const radioButton = e.target.closest('input[type="radio"]');
            if (radioButton) {
                const flashcard = radioButton.closest('.flashcard');
                if (flashcard) {
                    this.flashcardManager.handleAnswer(radioButton.value, flashcard);
                }
            }
        });
    }
}
