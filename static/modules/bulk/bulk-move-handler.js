/**
 * Handle bulk move operations for flashcards and decks
 * Leverages existing deck operations functionality
 */

// Import the functions from deck-operations.js
import { loadDeckList, populateDeckDropdown, setupDeckSearch } from "../deck/deck-operations.js";

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
            // Use the existing loadDeckList function from deck-operations.js
            const decks = await loadDeckList();
            
            // Clear existing options
            this.destDeckSelect.innerHTML = '<option value="" disabled selected>Select destination deck...</option>';
            
            // Use the shared populateDeckDropdown function
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
            // Use the existing loadDeckList function from deck-operations.js
            const decks = await loadDeckList({ hierarchical: true });
            
            // Clear existing options
            this.destSelect.innerHTML = '<option value="" disabled selected>Select parent deck...</option>';
            
            // Use the shared populateDeckDropdown function
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
    
    // Helper function to populate the deck options with proper indentation
    populateDeckOptions(decks, level, excludedIds = []) {
        // Process each deck in the tree structure
        decks.forEach(deck => {
            // Skip if this deck is in the excluded list
            if (!excludedIds.includes(deck.flashcard_deck_id)) {
                // Create option with proper indentation based on level
                const option = document.createElement('option');
                option.value = deck.flashcard_deck_id;
                
                // Add indentation based on level
                const indent = '  '.repeat(level);
                const prefix = level > 0 ? '└ ' : '';
                option.textContent = indent + prefix + deck.name;
                
                // Add to select element
                this.destSelect.appendChild(option);
                
                // Process child decks recursively
                if (deck.child_decks && deck.child_decks.length > 0) {
                    this.populateDeckOptions(deck.child_decks, level + 1, excludedIds);
                }
            }
        });
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
    
    // Add global functions
    window.showBulkMoveFlashcardModal = (flashcardIds, sourceDeckId) => {
        flashcardMover.show(flashcardIds, sourceDeckId);
    };
    
    window.showBulkMoveDeckModal = (deckIds) => {
        deckMover.show(deckIds);
    };
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initMovers);

export { initMovers, BulkFlashcardMover, BulkDeckMover };
