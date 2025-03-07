// Define these functions globally so they can be called from HTML before initialization
window.showImportModal = function() {
    console.log("Import modal requested");
    const modal = document.getElementById('importContentModal');
    if (modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
};

window.showGenerateModal = function() {
    console.log("Generate modal requested");
    const modal = document.getElementById('generateModal');
    if (modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
};

import { initializeDeckSearch } from './deck-search.js';

// Track if modals have been initialized to prevent duplicate handlers
let modalsInitialized = false;

export function initializeModals() {
    // Prevent duplicate initialization
    if (modalsInitialized) {
        console.log("Modals already initialized, skipping");
        return window._modalInstances || {};
    }
    
    console.log("Initializing modals");
    const modals = {};
    
    // Helper function to safely create modal
    const createModal = (elementId) => {
        const element = document.getElementById(elementId);
        return element ? new bootstrap.Modal(element) : null;
    };

    // Initialize modals only if their elements exist
    modals.deckModal = createModal('deckModal');
    modals.generateModal = createModal('generateModal');
    modals.noCardsModal = createModal('noCardsModal');
    modals.emptyDeckModal = createModal('createEmptyDeckModal');
    modals.deleteModal = createModal('deleteDeckModal');
    modals.importModal = createModal('importContentModal');

    let currentDeckId = null;

    // Create deck button handler
    setupButtonClickHandler('createDeckBtn', () => {
        console.log("Creating subdeck modal shown");
        const form = document.getElementById('createDeckForm');
        if (form) form.reset();
        if (modals.deckModal) modals.deckModal.show();
    });

    // Empty deck button handler
    setupButtonClickHandler('createEmptyDeckBtn', () => {
        console.log("Creating empty deck modal shown");
        const form = document.getElementById('createEmptyDeckForm');
        if (form) form.reset();
        if (modals.emptyDeckModal) modals.emptyDeckModal.show();
    });

    // Add cards button handlers
    document.querySelectorAll('.add-cards-btn').forEach(button => {
        button.addEventListener('click', () => {
            const form = document.getElementById('generateForm');
            if (form) form.reset();
            
            const parentDeckIdInput = document.getElementById('generateParentDeckId');
            if (parentDeckIdInput) {
                parentDeckIdInput.value = button.dataset.deckId;
            }
            
            if (modals.generateModal) modals.generateModal.show();
        });
    });

    // No cards handlers
    if (modals.noCardsModal) {
        // Attach event to dropdown buttons with no-cards class
        document.querySelectorAll('.dropdown-toggle.no-cards').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                currentDeckId = button.dataset.deckId;
                modals.noCardsModal.show();
                
                // Prevent dropdown from opening
                e.stopPropagation();
            });
        });
        
        // Also attach to dropdown items with no-cards class
        document.querySelectorAll('.dropdown-item.no-cards').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                currentDeckId = link.dataset.deckId;
                modals.noCardsModal.show();
            });
        });
    }

    // Generate from no cards handler
    const generateFromNoCards = document.getElementById('generateFromNoCards');
    if (generateFromNoCards && modals.noCardsModal && modals.generateModal) {
        generateFromNoCards.addEventListener('click', () => {
            modals.noCardsModal.hide();
            const form = document.getElementById('generateForm');
            if (form) form.reset();
            
            const parentDeckIdInput = document.getElementById('generateParentDeckId');
            if (parentDeckIdInput) {
                parentDeckIdInput.value = currentDeckId;
            }
            
            modals.generateModal.show();
        });
    }

    // Override the global functions now that we have proper modal instances
    if (modals.importModal) {
        window.showImportModal = () => {
            // Reset the form if needed
            const importFileForm = document.getElementById('importFileForm');
            if (importFileForm) {
                importFileForm.reset();
            }
            
            // Show the modal
            modals.importModal.show();
        };
    }

    if (modals.generateModal) {
        window.showGenerateModal = () => {
            const form = document.getElementById('generateForm');
            if (form) form.reset();
            modals.generateModal.show();
        };
    }

    // Initialize deck search in all relevant modals
    document.querySelectorAll('.deck-search-select').forEach(selectElement => {
        selectElement.classList.remove('searchable-select');
        initializeDeckSearch(selectElement);
    });
    
    // For modals that might load dynamically
    document.addEventListener('shown.bs.modal', function(event) {
        const modal = event.target;
        if (modal) {
            const selectElements = modal.querySelectorAll('.deck-search-select');
            selectElements.forEach(selectElement => {
                selectElement.classList.remove('searchable-select');
                initializeDeckSearch(selectElement);
            });
        }
    });

    // Mark as initialized
    modalsInitialized = true;
    
    // Store instances globally for debugging
    window._modalInstances = modals;

    return modals;
}

// Helper function to set up button click handlers
function setupButtonClickHandler(buttonId, handler) {
    const button = document.getElementById(buttonId);
    if (button) {
        // For mobile menu items that have the same ID, we need to handle them specially
        if (buttonId === 'createEmptyDeckBtn' || buttonId === 'createDeckBtn') {
            // Find all elements with this ID or data-target matching this ID
            document.querySelectorAll(`#${buttonId}, [data-target="#${buttonId}"]`).forEach(element => {
                element.addEventListener('click', (e) => {
                    e.preventDefault();
                    console.log(`Button clicked: ${buttonId}`);
                    handler();
                });
            });
        } else {
            // Regular button handling
            button.addEventListener('click', (e) => {
                e.preventDefault();
                console.log(`Button clicked: ${buttonId}`);
                handler();
            });
        }
    } else {
        console.log(`Button with ID ${buttonId} not found`);
    }
}
