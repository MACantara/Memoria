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

export function initializeModals() {
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
    modals.importModal = createModal('importContentModal');  // Add import modal

    let currentDeckId = null;

    // Create deck button handler
    const createDeckBtn = document.getElementById('createDeckBtn');
    if (createDeckBtn && modals.deckModal) {
        createDeckBtn.onclick = () => {
            document.getElementById('createDeckForm').reset();
            modals.deckModal.show();
        };
    }

    // Empty deck button handler
    const createEmptyDeckBtn = document.getElementById('createEmptyDeckBtn');
    if (createEmptyDeckBtn && modals.emptyDeckModal) {
        createEmptyDeckBtn.onclick = () => {
            document.getElementById('createEmptyDeckForm').reset();
            modals.emptyDeckModal.show();
        };
    }

    // Add cards button handlers
    if (modals.generateModal) {
        document.querySelectorAll('.add-cards-btn').forEach(button => {
            button.addEventListener('click', () => {
                const form = document.getElementById('generateForm');
                form.reset();
                const parentDeckIdInput = document.getElementById('generateParentDeckId');
                if (parentDeckIdInput) {
                    parentDeckIdInput.value = button.dataset.deckId;
                }
                modals.generateModal.show();
            });
        });
    }

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
            form.reset();
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
            document.getElementById('generateForm').reset();
            modals.generateModal.show();
        };
    }

    return modals;
}
