import { initializeDeckSearch } from './deck-search.js';

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

    // Create deck button handler - use {once: true} to ensure it only runs once
    const createDeckBtn = document.getElementById('createDeckBtn');
    if (createDeckBtn && modals.deckModal) {
        // Remove any existing click handlers first
        createDeckBtn.removeEventListener('click', showCreateDeckModal);
        createDeckBtn.addEventListener('click', showCreateDeckModal, {once: false});
    }

    function showCreateDeckModal() {
        document.getElementById('createDeckForm').reset();
        modals.deckModal.show();
    }

    // Empty deck button handler
    const createEmptyDeckBtn = document.getElementById('createEmptyDeckBtn');
    if (createEmptyDeckBtn && modals.emptyDeckModal) {
        // Remove any existing click handlers first
        createEmptyDeckBtn.removeEventListener('click', showEmptyDeckModal);
        createEmptyDeckBtn.addEventListener('click', showEmptyDeckModal, {once: false});
    }

    function showEmptyDeckModal() {
        document.getElementById('createEmptyDeckForm').reset();
        modals.emptyDeckModal.show();
    }

    // Add cards button handlers
    if (modals.generateModal) {
        document.querySelectorAll('.add-cards-btn').forEach(button => {
            // Remove any existing handlers first
            button.removeEventListener('click', handleAddCardsClick);
            button.addEventListener('click', handleAddCardsClick, {once: false});
        });
    }

    function handleAddCardsClick(event) {
        const form = document.getElementById('generateForm');
        form.reset();
        const parentDeckIdInput = document.getElementById('generateParentDeckId');
        if (parentDeckIdInput) {
            parentDeckIdInput.value = event.currentTarget.dataset.deckId;
        }
        modals.generateModal.show();
    }

    // No cards handlers
    if (modals.noCardsModal) {
        // Attach event to dropdown buttons with no-cards class
        document.querySelectorAll('.dropdown-toggle.no-cards').forEach(button => {
            // Remove any existing handlers first
            button.removeEventListener('click', handleNoCardsClick);
            button.addEventListener('click', handleNoCardsClick, {once: false});
        });
        
        // Also attach to dropdown items with no-cards class
        document.querySelectorAll('.dropdown-item.no-cards').forEach(link => {
            // Remove any existing handlers first
            link.removeEventListener('click', handleNoCardsClick);
            link.addEventListener('click', handleNoCardsClick, {once: false});
        });
    }

    function handleNoCardsClick(event) {
        event.preventDefault();
        currentDeckId = event.currentTarget.dataset.deckId;
        modals.noCardsModal.show();
        
        // Prevent dropdown from opening
        event.stopPropagation();
    }

    // Generate from no cards handler
    const generateFromNoCards = document.getElementById('generateFromNoCards');
    if (generateFromNoCards && modals.noCardsModal && modals.generateModal) {
        // Remove any existing handlers first
        generateFromNoCards.removeEventListener('click', handleGenerateFromNoCards);
        generateFromNoCards.addEventListener('click', handleGenerateFromNoCards, {once: false});
    }

    function handleGenerateFromNoCards() {
        modals.noCardsModal.hide();
        const form = document.getElementById('generateForm');
        form.reset();
        const parentDeckIdInput = document.getElementById('generateParentDeckId');
        if (parentDeckIdInput) {
            parentDeckIdInput.value = currentDeckId;
        }
        modals.generateModal.show();
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
            document.getElementById('generateForm').reset();
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
