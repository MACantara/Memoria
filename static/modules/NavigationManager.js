export class NavigationManager {
    constructor(flashcardManager) {
        this.flashcardManager = flashcardManager;
        this.prevButton = document.getElementById('prevCard');
        this.nextButton = document.getElementById('nextCard');
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
            this.flashcardManager.handleKeyboardNavigation(e.key);
        });
    }
}
