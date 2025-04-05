/**
 * Handle bulk move operations for flashcards and decks
 * Leverages existing deck operations functionality
 */

// Fix import to only include functions that actually exist in deck-operations.js
import { loadDeckTree } from "../deck/deck-operations.js";

// Define global functions at module scope so they can be exported and used elsewhere
export function showBulkMoveFlashcardModal(flashcardIds, sourceDeckId) {
    // Initialize if necessary
    if (!flashcardMover) {
        initMovers();
    }
    flashcardMover.show(flashcardIds, sourceDeckId);
}

export function showBulkMoveDeckModal(deckIds) {
    // Initialize if necessary
    if (!deckMover) {
        initMovers();
    }
    deckMover.show(deckIds);
}

/**
 * Populate a select dropdown with deck options
 * @param {HTMLSelectElement} selectElement - The select element to populate
 * @param {Array} decks - Array of deck objects
 * @param {Object} options - Configuration options
 */
function populateDeckDropdown(selectElement, decks, options = {}) {
    const defaults = {
        excludeDeckIds: [],
        hierarchical: false,
        flatList: false,
        valueProperty: 'id',
        textProperty: 'name',
        childrenProperty: 'child_decks'
    };
    
    const config = { ...defaults, ...options };
    
    // If hierarchical and not flat list, populate recursively with indentation
    if (config.hierarchical && !config.flatList) {
        populateDeckOptionsHierarchical(
            selectElement, 
            decks, 
            0, 
            config.excludeDeckIds, 
            config.valueProperty, 
            config.textProperty, 
            config.childrenProperty
        );
    } else {
        // Flat list, just add all decks directly
        decks.forEach(deck => {
            // Skip if this deck is in the excluded list
            if (!config.excludeDeckIds.includes(deck[config.valueProperty])) {
                const option = document.createElement('option');
                option.value = deck[config.valueProperty];
                option.textContent = deck[config.textProperty];
                selectElement.appendChild(option);
            }
        });
    }
}

/**
 * Populate select with hierarchical deck options (with indentation)
 */
function populateDeckOptionsHierarchical(
    selectElement, 
    decks, 
    level, 
    excludedIds = [], 
    valueProperty = 'flashcard_deck_id', 
    textProperty = 'name', 
    childrenProperty = 'child_decks'
) {
    // Process each deck in the tree structure
    decks.forEach(deck => {
        // Skip if this deck is in the excluded list
        if (!excludedIds.includes(deck[valueProperty])) {
            // Create option with proper indentation based on level
            const option = document.createElement('option');
            option.value = deck[valueProperty];
            
            // Add indentation based on level
            const indent = '  '.repeat(level);
            const prefix = level > 0 ? '└ ' : '';
            option.textContent = indent + prefix + deck[textProperty];
            
            // Add to select element
            selectElement.appendChild(option);
            
            // Process child decks recursively
            if (deck[childrenProperty] && deck[childrenProperty].length > 0) {
                populateDeckOptionsHierarchical(
                    selectElement, 
                    deck[childrenProperty], 
                    level + 1, 
                    excludedIds,
                    valueProperty,
                    textProperty,
                    childrenProperty
                );
            }
        }
    });
}

/**
 * Set up search functionality for a deck select dropdown
 */
function setupDeckSearch(searchInput, selectElement) {
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const options = selectElement.querySelectorAll('option:not([disabled])');
        
        options.forEach(option => {
            const text = option.textContent.toLowerCase();
            if (text.includes(searchTerm)) {
                option.style.display = '';
            } else {
                option.style.display = 'none';
            }
        });
    });
}

// Bulk move flashcards modal handling
class BulkFlashcardMover {
    constructor() {
        this.modal = document.getElementById('bulkMoveFlashcardsModal');
        this.selectedIds = [];
        this.destDeckSelect = document.getElementById('bulkDestDeckSelect');
        this.moveButton = document.getElementById('bulkMoveButton');
        this.statusElement = document.getElementById('bulkMoveStatus');
        this.sourceDeckId = null;
        
        this.initModal();
    }
    
    initModal() {
        // Set up event handlers
        if (this.moveButton) {
            this.moveButton.addEventListener('click', () => this.performMove());
        }
        
        // Set up search functionality
        const searchInput = document.getElementById('bulkDestDeckSearchInput');
        if (searchInput && this.destDeckSelect) {
            setupDeckSearch(searchInput, this.destDeckSelect);
        }
    }
    
    async loadDecks(excludeDeckId = null) {
        // Store source deck ID to exclude it from destination options
        this.sourceDeckId = excludeDeckId;
        
        try {
            // Use the existing loadDeckTree function from deck-operations.js
            const decks = await loadDeckTree();
            
            // Clear existing options
            this.destDeckSelect.innerHTML = '<option value="" disabled selected>Select destination deck...</option>';
            
            // Use our local populateDeckDropdown function
            populateDeckDropdown(this.destDeckSelect, decks, {
                excludeDeckIds: [excludeDeckId], // Exclude the source deck
                flatList: true, // Use flat list instead of hierarchical for flashcard moves
                valueProperty: 'id',
                textProperty: 'name'
            });
        } catch (error) {
            console.error('Error loading decks:', error);
            this.statusElement.innerHTML = `
                <div class="alert alert-danger">
                    Error loading decks. Please try again.
                </div>
            `;
        }
    }
    
    show(flashcardIds, sourceDeckId = null) {
        this.selectedIds = flashcardIds;
        
        // Load deck options
        this.loadDecks(sourceDeckId);
        
        // Update UI
        const countElement = this.modal.querySelector('.selected-count');
        if (countElement) {
            countElement.textContent = flashcardIds.length;
        }
        
        // Reset status
        if (this.statusElement) {
            this.statusElement.innerHTML = '';
        }
        
        // Reset button
        if (this.moveButton) {
            this.moveButton.disabled = false;
            const normalState = this.moveButton.querySelector('.normal-state');
            const loadingState = this.moveButton.querySelector('.loading-state');
            
            if (normalState) normalState.classList.remove('d-none');
            if (loadingState) loadingState.classList.add('d-none');
        }
        
        // Show modal
        const bsModal = new bootstrap.Modal(this.modal);
        bsModal.show();
    }
    
    async performMove() {
        if (!this.destDeckSelect.value || this.selectedIds.length === 0) {
            this.statusElement.innerHTML = `
                <div class="alert alert-warning">
                    Please select a destination deck.
                </div>
            `;
            return;
        }
        
        // Update button state
        this.moveButton.disabled = true;
        const normalState = this.moveButton.querySelector('.normal-state');
        const loadingState = this.moveButton.querySelector('.loading-state');
        
        if (normalState) normalState.classList.add('d-none');
        if (loadingState) loadingState.classList.remove('d-none');
        
        try {
            // Call API to move flashcards
            const response = await fetch('/deck/api/flashcards/bulk-move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    flashcard_ids: this.selectedIds,
                    destination_deck_id: this.destDeckSelect.value
                }),
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.statusElement.innerHTML = `
                    <div class="alert alert-success">
                        Successfully moved ${result.moved_count} flashcards.
                    </div>
                `;
                
                // Refresh page after a delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                this.statusElement.innerHTML = `
                    <div class="alert alert-danger">
                        ${result.error || 'An error occurred while moving flashcards.'}
                    </div>
                `;
                
                // Reset button
                this.moveButton.disabled = false;
                if (normalState) normalState.classList.remove('d-none');
                if (loadingState) loadingState.classList.add('d-none');
            }
        } catch (error) {
            console.error('Move error:', error);
            this.statusElement.innerHTML = `
                <div class="alert alert-danger">
                    An error occurred while moving flashcards.
                </div>
            `;
            
            // Reset button
            this.moveButton.disabled = false;
            if (normalState) normalState.classList.remove('d-none');
            if (loadingState) loadingState.classList.add('d-none');
        }
    }
}

// Bulk move decks modal handling
class BulkDeckMover {
    constructor() {
        this.modal = document.getElementById('bulkMoveDecksModal');
        this.selectedIds = [];
        this.destSelect = document.getElementById('bulkParentDeckSelect');
        this.moveButton = document.getElementById('bulkMoveDeckButton');
        this.statusElement = document.getElementById('bulkMoveDeckStatus');
        
        this.initModal();
    }
    
    initModal() {
        // Set up event handlers
        document.querySelectorAll('input[name="bulkDestDeck"]').forEach(radio => {
            radio.addEventListener('change', () => {
                const subdeckContainer = document.getElementById('bulkParentDeckSelectContainer');
                if (radio.value === 'subdeck') {
                    subdeckContainer.classList.remove('d-none');
                    this.destSelect.disabled = false;
                } else {
                    subdeckContainer.classList.add('d-none');
                    this.destSelect.disabled = true;
                }
            });
        });
        
        if (this.moveButton) {
            this.moveButton.addEventListener('click', () => this.performMove());
        }
        
        // Set up search functionality
        const searchInput = document.getElementById('bulkParentDeckSearchInput');
        if (searchInput && this.destSelect) {
            setupDeckSearch(searchInput, this.destSelect);
        }
    }
    
    async loadDecks() {
        try {
            // Use the existing loadDeckTree function from deck-operations.js
            const decks = await loadDeckTree({ hierarchical: true });
            
            // Clear existing options
            this.destSelect.innerHTML = '<option value="" disabled selected>Select parent deck...</option>';
            
            // Use our local populateDeckDropdown function
            populateDeckDropdown(this.destSelect, decks, {
                excludeDeckIds: this.selectedIds, // Exclude selected decks
                hierarchical: true, // Use hierarchical format for deck moves
                valueProperty: 'flashcard_deck_id',
                textProperty: 'name',
                childrenProperty: 'child_decks'
            });
        } catch (error) {
            console.error('Error loading decks:', error);
            this.statusElement.innerHTML = `
                <div class="alert alert-danger">
                    <p><i class="bi bi-exclamation-triangle me-2"></i>Error loading decks</p>
                    <p class="small mb-0">Please try again or refresh the page. Error: ${error.message}</p>
                </div>
            `;
            
            // Try to provide a working UI even after error
            this.destSelect.innerHTML = '<option value="" disabled selected>Failed to load decks</option>';
            
            // Disable the move button temporarily since we can't properly select a destination
            if (this.moveButton) {
                this.moveButton.disabled = true;
            }
        }
    }
    
    show(deckIds) {
        this.selectedIds = deckIds;
        
        // Load deck options, excluding selected decks
        this.loadDecks();
        
        // Update UI
        const countElement = this.modal.querySelector('.selected-count');
        if (countElement) {
            countElement.textContent = deckIds.length;
        }
        
        // Reset status
        if (this.statusElement) {
            this.statusElement.innerHTML = '';
        }
        
        // Reset button
        if (this.moveButton) {
            this.moveButton.disabled = false;
            const normalState = this.moveButton.querySelector('.normal-state');
            const loadingState = this.moveButton.querySelector('.loading-state');
            
            if (normalState) normalState.classList.remove('d-none');
            if (loadingState) loadingState.classList.add('d-none');
        }
        
        // Reset radio buttons
        const rootRadio = document.getElementById('bulkRootDeck');
        if (rootRadio) {
            rootRadio.checked = true;
            const subdeckContainer = document.getElementById('bulkParentDeckSelectContainer');
            if (subdeckContainer) {
                subdeckContainer.classList.add('d-none');
            }
            if (this.destSelect) {
                this.destSelect.disabled = true;
            }
        }
        
        // Show modal
        const bsModal = new bootstrap.Modal(this.modal);
        bsModal.show();
    }
    
    async performMove() {
        const useParent = document.getElementById('bulkSubdeckOption').checked;
        let parentId = null;
        
        if (useParent) {
            if (!this.destSelect.value) {
                this.statusElement.innerHTML = `
                    <div class="alert alert-warning">
                        Please select a parent deck.
                    </div>
                `;
                return;
            }
            parentId = this.destSelect.value;
        }
        
        // Update button state
        this.moveButton.disabled = true;
        const normalState = this.moveButton.querySelector('.normal-state');
        const loadingState = this.moveButton.querySelector('.loading-state');
        
        if (normalState) normalState.classList.add('d-none');
        if (loadingState) loadingState.classList.remove('d-none');
        
        try {
            // Call API to move decks
            const response = await fetch('/deck/api/decks/bulk-move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    deck_ids: this.selectedIds,
                    parent_deck_id: parentId
                }),
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.statusElement.innerHTML = `
                    <div class="alert alert-success">
                        Successfully moved ${result.moved_count} decks.
                    </div>
                `;
                
                // Refresh page after a delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                this.statusElement.innerHTML = `
                    <div class="alert alert-danger">
                        ${result.error || 'An error occurred while moving decks.'}
                    </div>
                `;
                
                // Reset button
                this.moveButton.disabled = false;
                if (normalState) normalState.classList.remove('d-none');
                if (loadingState) loadingState.classList.add('d-none');
            }
        } catch (error) {
            console.error('Move error:', error);
            this.statusElement.innerHTML = `
                <div class="alert alert-danger">
                    An error occurred while moving decks.
                </div>
            `;
            
            // Reset button
            this.moveButton.disabled = false;
            if (normalState) normalState.classList.remove('d-none');
            if (loadingState) loadingState.classList.add('d-none');
        }
    }
}

// Initialize both movers
let flashcardMover = null;
let deckMover = null;

function initMovers() {
    flashcardMover = new BulkFlashcardMover();
    deckMover = new BulkDeckMover();
    
    // Also make functions available globally on window for non-module contexts
    window.showBulkMoveFlashcardModal = showBulkMoveFlashcardModal;
    window.showBulkMoveDeckModal = showBulkMoveDeckModal;
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initMovers);

export { initMovers, BulkFlashcardMover, BulkDeckMover };
