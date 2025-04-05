/**
 * Handle bulk move operations for flashcards and decks
 * Self-contained module with no external dependencies
 */

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
 * Fetch deck list from the API
 * @param {Object} options - Options for fetching decks
 * @returns {Promise<Array>} Array of deck objects
 */
async function loadDeckTree(options = {}) {
    const defaults = {
        hierarchical: false
    };
    
    const config = { ...defaults, ...options };
    
    try {
        // Choose the appropriate API endpoint based on hierarchical option
        const endpoint = config.hierarchical 
            ? '/deck/api/decks/tree'  // Hierarchical structure with parent-child relationships
            : '/deck/api/list';       // Flat list of all decks
            
        const response = await fetch(endpoint);
        
        if (!response.ok) {
            // If the endpoint fails, try the alternate endpoint
            console.warn(`${endpoint} returned ${response.status}, falling back to alternate endpoint`);
            const fallbackEndpoint = config.hierarchical 
                ? '/deck/api/list'       // Fallback for tree
                : '/deck/api/decks/tree'; // Fallback for list
                
            const fallbackResponse = await fetch(fallbackEndpoint);
            
            if (!fallbackResponse.ok) {
                throw new Error(`API endpoints failed: ${fallbackResponse.status} ${fallbackResponse.statusText}`);
            }
            
            const fallbackData = await fallbackResponse.json();
            
            // If we needed hierarchical but got flat, convert it
            if (config.hierarchical && fallbackEndpoint === '/deck/api/list') {
                return convertFlatToTree(fallbackData);
            }
            
            // If we needed flat but got hierarchical, flatten it
            if (!config.hierarchical && fallbackEndpoint === '/deck/api/decks/tree') {
                return flattenTree(fallbackData);
            }
            
            return fallbackData;
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error loading decks:', error);
        throw error;
    }
}

/**
 * Convert flat deck list to hierarchical tree
 * @param {Array} flatDecks - Flat array of deck objects
 * @returns {Array} Hierarchical tree of deck objects
 */
function convertFlatToTree(flatDecks) {
    // Create a map to quickly find decks by ID
    const deckMap = new Map();
    const rootDecks = [];
    
    // First pass: Create deck objects and store in map
    flatDecks.forEach(deck => {
        const deckObj = {
            flashcard_deck_id: deck.id,
            name: deck.name,
            description: deck.description || '',
            parent_id: deck.parent_id,
            child_decks: []
        };
        deckMap.set(deck.id, deckObj);
    });
    
    // Second pass: Build hierarchy by adding children
    flatDecks.forEach(deck => {
        const deckObj = deckMap.get(deck.id);
        
        if (deck.parent_id) {
            // Add to parent's children
            const parent = deckMap.get(deck.parent_id);
            if (parent) {
                parent.child_decks.push(deckObj);
            } else {
                // Parent not found, add to root level
                rootDecks.push(deckObj);
            }
        } else {
            // No parent, add to root level
            rootDecks.push(deckObj);
        }
    });
    
    return rootDecks;
}

/**
 * Flatten hierarchical tree into a list
 * @param {Array} tree - Hierarchical tree of deck objects
 * @returns {Array} Flat array of deck objects
 */
function flattenTree(tree) {
    const flatList = [];
    
    function traverse(deck) {
        // Convert deck format if needed
        const flatDeck = {
            id: deck.flashcard_deck_id,
            name: deck.name,
            description: deck.description,
            parent_id: deck.parent_deck_id
        };
        
        flatList.push(flatDeck);
        
        // Traverse children if any
        if (deck.child_decks && deck.child_decks.length > 0) {
            deck.child_decks.forEach(traverse);
        }
    }
    
    tree.forEach(traverse);
    return flatList;
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
            // Use our local loadDeckTree function
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
            // Use our local loadDeckTree function
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
