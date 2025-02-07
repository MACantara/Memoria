import { FormHandler } from './modules/FormHandler.js';
import { FlashcardManager } from './modules/FlashcardManager.js';
import { NavigationManager } from './modules/NavigationManager.js';
import { EventManager } from './modules/EventManager.js';

document.addEventListener('DOMContentLoaded', function() {
    const formHandler = new FormHandler();
    const flashcardManager = new FlashcardManager();
    const navigationManager = new NavigationManager(flashcardManager);
    const eventManager = new EventManager(flashcardManager, navigationManager);

    eventManager.initialize();
});