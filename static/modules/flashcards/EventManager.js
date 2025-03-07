/**
 * EventManager - Handles DOM events and delegates to the appropriate manager
 */
export class EventManager {
    /**
     * @param {Object} flashcardManager - Reference to the FlashcardManager instance
     * @param {Object} uiManager - Reference to the UIManager instance
     */
    constructor(flashcardManager, uiManager) {
        this.manager = flashcardManager;
        this.ui = uiManager;
        this.answerForm = document.getElementById('answerForm');
        this.flashcardContainer = document.getElementById('flashcardsContainer');
    }
    
    /**
     * Set up all event listeners needed for the flashcard UI
     */
    setupEventListeners() {
        // Set up answer form submission (delegation)
        if (this.answerForm) {
            this.answerForm.addEventListener('click', (e) => {
                const answerOption = e.target.closest('.answer-option');
                if (answerOption) {
                    const radio = answerOption.querySelector('input[type="radio"]');
                    if (radio && !radio.checked) {
                        radio.checked = true;
                        
                        // Notify FlashcardManager about the answer
                        this.manager.handleAnswer(radio.value);
                    }
                }
            });
        }
        
        // Set up keyboard navigation events
        document.addEventListener('keydown', (e) => {
            // Ignore key events if there's an active dialog, modal, or if in a text field
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }
            
            this.manager.handleKeyboardNavigation(e.key);
        });
        
        // Handle swipe gestures for mobile (optional)
        this.setupMobileGestures();
    }
    
    /**
     * Set up touch swipe gestures for mobile navigation
     */
    setupMobileGestures() {
        if (!this.flashcardContainer) return;
        
        let touchStartX = 0;
        let touchEndX = 0;
        
        this.flashcardContainer.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        });
        
        this.flashcardContainer.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            this.handleSwipe(touchStartX, touchEndX);
        });
    }
    
    /**
     * Handle swipe gesture
     * @param {number} startX - Touch start X position
     * @param {number} endX - Touch end X position
     */
    handleSwipe(startX, endX) {
        const threshold = 100; // Minimum swipe distance
        
        // Handle swipe left (next card)
        if (startX - endX > threshold) {
            // Only proceed if we're in an answer feedback state with a "Next" button
            const nextButton = document.querySelector('.feedback-container .btn');
            if (nextButton) {
                nextButton.click();
            }
        }
        
        // Handle swipe right (previous card) - currently disabled as not needed
        // if (endX - startX > threshold) {
        //     this.manager.showPreviousCard();
        // }
    }
    
    /**
     * Remove all event listeners (for cleanup)
     */
    cleanup() {
        // If needed, we can implement this to remove event listeners
        // when the flashcard component is destroyed
    }
}
