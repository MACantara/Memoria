import { FormHandler } from './modules/flashcards/FormHandler.js';
import { FlashcardManager } from './modules/flashcards/FlashcardManager.js';
import { NavigationManager } from './modules/flashcards/NavigationManager.js';
import { EventManager } from './modules/flashcards/EventManager.js';

document.addEventListener('DOMContentLoaded', function() {
    const formHandler = new FormHandler();
    const flashcardManager = new FlashcardManager();
    const navigationManager = new NavigationManager(flashcardManager);
    const eventManager = new EventManager(flashcardManager, navigationManager);

    eventManager.initialize();
});