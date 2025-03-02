import { renameDeck } from '../utils.js';

export function initializeDeckOperations() {
    let deckToDelete = null;
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteDeckModal'));
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    window.deleteDeck = async (deckId) => {
        deckToDelete = deckId;
        deleteModal.show();
    };
    
    window.showRenameDeckModal = (deckId, currentName, currentDescription) => {
        const modal = new bootstrap.Modal(document.getElementById('renameDeckModal'));
        document.getElementById('deckId').value = deckId;
        document.getElementById('newDeckName').value = currentName;
        document.getElementById('newDeckDescription').value = currentDescription;
        document.getElementById('renameStatus').innerHTML = '';
        modal.show();
    };

    document.getElementById('renameDeckForm').addEventListener('submit', handleRenameSubmit);
    document.getElementById('confirmDeleteBtn').addEventListener('click', () => handleDelete(deckToDelete));
    
    // Initialize move deck functionality
    initializeMoveDeck();

    // Add this new function to load due counts for each deck
    loadDueCounts();
}

async function handleRenameSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const normalState = submitButton.querySelector('.normal-state');
    const loadingState = submitButton.querySelector('.loading-state');
    const statusDiv = document.getElementById('renameStatus');

    submitButton.disabled = true;
    normalState.classList.add('d-none');
    loadingState.classList.remove('d-none');

    try {
        const deckId = document.getElementById('deckId').value;
        const newName = document.getElementById('newDeckName').value;
        const newDescription = document.getElementById('newDeckDescription').value;
        const result = await renameDeck(deckId, newName, newDescription);
        
        if (result.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> Deck renamed successfully!
                </div>
            `;
            setTimeout(() => location.reload(), 1000);
        } else {
            throw new Error(result.error || 'Failed to rename deck');
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> ${error.message}
            </div>
        `;
        submitButton.disabled = false;
        normalState.classList.remove('d-none');
        loadingState.classList.add('d-none');
    }
}

async function handleDelete(deckToDelete) {
    const button = document.getElementById('confirmDeleteBtn');
    const normalState = button.querySelector('.normal-state');
    const loadingState = button.querySelector('.loading-state');
    const statusDiv = document.getElementById('deleteStatus');
    
    button.disabled = true;
    normalState.classList.add('d-none');
    loadingState.classList.remove('d-none');
    
    try {
        const response = await fetch(`/deck/delete/${deckToDelete}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> ${data.message}
                </div>
            `;
            setTimeout(() => location.reload(), 2000);
        } else {
            throw new Error(data.error || 'Failed to delete deck');
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> ${error.message}
            </div>
        `;
        button.disabled = false;
        normalState.classList.remove('d-none');
        loadingState.classList.add('d-none');
    }
}

function initializeMoveDeck() {
    let currentDeckId = null;
    let currentDeckName = null;
    const moveDeckModal = document.getElementById('moveDeckModal');
    if (!moveDeckModal) return;
    
    const rootDeckOption = document.getElementById('rootDeck');
    const subdeckOption = document.getElementById('subdeckOption');
    const parentDeckSelect = document.getElementById('parentDeckSelect');
    const parentDeckSelectContainer = document.getElementById('parentDeckSelectContainer');
    const parentDeckInfo = document.getElementById('parentDeckInfo');
    const parentDeckPath = document.getElementById('parentDeckPath');
    const circularReferenceWarning = document.getElementById('circularReferenceWarning');
    const deckToMoveName = document.getElementById('deckToMoveName');
    const confirmMoveBtn = document.getElementById('confirmMoveBtn');
    
    // Set up radio button change handlers
    rootDeckOption.addEventListener('change', function() {
        if (this.checked) {
            parentDeckSelect.disabled = true;
            parentDeckSelectContainer.classList.add('d-none');
            confirmMoveBtn.disabled = false;
        }
    });
    
    subdeckOption.addEventListener('change', function() {
        if (this.checked) {
            parentDeckSelect.disabled = false;
            parentDeckSelectContainer.classList.remove('d-none');
            
            // Reevaluate the confirmation button state
            checkMoveValidity();
        }
    });
    
    // Handle parent deck selection change
    parentDeckSelect.addEventListener('change', function() {
        const selectedDeckId = this.value;
        
        // Clear previous info
        parentDeckInfo.classList.add('d-none');
        circularReferenceWarning.classList.add('d-none');
        
        if (selectedDeckId) {
            // Check for circular reference
            if (selectedDeckId === currentDeckId) {
                circularReferenceWarning.classList.remove('d-none');
                confirmMoveBtn.disabled = true;
                return;
            }
            
            // Show parent info if available
            const selectedOption = this.options[this.selectedIndex];
            const parentName = selectedOption.dataset.parent;
            
            if (parentName) {
                parentDeckPath.textContent = `Parent deck: ${parentName} > ${selectedOption.text}`;
                parentDeckInfo.classList.remove('d-none');
            } else {
                parentDeckPath.textContent = `This is a top-level deck`;
                parentDeckInfo.classList.remove('d-none');
            }
            
            // Enable move button
            confirmMoveBtn.disabled = false;
        } else {
            // No selection, disable move button
            confirmMoveBtn.disabled = true;
        }
    });
    
    // Prepare the modal when it's shown
    moveDeckModal.addEventListener('show.bs.modal', function(event) {
        // Only try to get data from relatedTarget if it exists
        // This fixes the undefined getAttribute error
        if (event.relatedTarget) {
            currentDeckId = event.relatedTarget.getAttribute('data-deck-id');
            currentDeckName = event.relatedTarget.getAttribute('data-deck-name');
        }
        
        // Set the deck name (use the stored values that might have been set by showMoveDeckModal)
        if (currentDeckName) {
            deckToMoveName.textContent = currentDeckName;
        }
        
        // Reset the modal
        rootDeckOption.checked = true;
        parentDeckSelect.disabled = true;
        parentDeckSelectContainer.classList.add('d-none');
        parentDeckInfo.classList.add('d-none');
        circularReferenceWarning.classList.add('d-none');
        confirmMoveBtn.disabled = false;
        
        // Remove the current deck and its children from options
        for (let i = 0; i < parentDeckSelect.options.length; i++) {
            const option = parentDeckSelect.options[i];
            
            // Skip placeholder option
            if (option.disabled && option.selected) continue;
            
            // Check if this is the current deck or a child of it
            // For now, a simple check if it's the same deck
            if (option.value === currentDeckId) {
                option.disabled = true;
                option.style.display = 'none';
            } else {
                option.disabled = false;
                option.style.display = '';
            }
        }
        
        // Reset the selection
        parentDeckSelect.selectedIndex = 0;
    });
    
    // Add move confirmation handler
    confirmMoveBtn.addEventListener('click', function() {
        handleMoveConfirm(currentDeckId);
    });
    
    // Make showMoveDeckModal available globally for button handling
    window.showMoveDeckModal = (deckId, deckName) => {
        // Store the deck ID and name for use in the modal
        currentDeckId = deckId;
        currentDeckName = deckName;
        
        // Get the modal element
        const modalElement = document.getElementById('moveDeckModal');
        if (!modalElement) return;
        
        // Update the deck name directly here
        const deckNameElement = document.getElementById('deckToMoveName');
        if (deckNameElement) {
            deckNameElement.textContent = deckName;
        }
        
        // Show the modal
        const bsModal = new bootstrap.Modal(modalElement);
        bsModal.show();
    };
    
    // Helper function to check if the move is valid
    function checkMoveValidity() {
        if (subdeckOption.checked && (!parentDeckSelect.value || parentDeckSelect.value === currentDeckId)) {
            confirmMoveBtn.disabled = true;
        } else {
            confirmMoveBtn.disabled = false;
        }
    }
}

async function loadDeckTree(currentDeckId) {
    try {
        const response = await fetch('/deck/api/decks/tree');
        const decks = await response.json();
        
        const treeHtml = renderDeckTree(decks, 0, currentDeckId);
        document.getElementById('deckTreeContainer').innerHTML = treeHtml || '<div class="text-muted">No other decks available</div>';
    } catch (error) {
        console.error('Error loading deck tree:', error);
        document.getElementById('deckTreeContainer').innerHTML = 
            '<div class="alert alert-danger">Failed to load decks</div>';
    }
}

function renderDeckTree(decks, level, currentDeckId) {
    if (!decks || decks.length === 0) return '';
    
    let html = '<ul class="deck-tree" style="list-style-type: none; padding-left: ' + 
               (level > 0 ? '20px' : '0') + ';">';
    
    decks.forEach(deck => {
        // Skip the current deck and its descendants
        if (deck.flashcard_deck_id == currentDeckId) return;
        
        html += `
            <li class="mb-2">
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="destinationDeck" 
                           id="deck${deck.flashcard_deck_id}" value="${deck.flashcard_deck_id}">
                    <label class="form-check-label" for="deck${deck.flashcard_deck_id}">
                        <i class="bi bi-folder"></i> ${deck.name}
                    </label>
                </div>
            `;
        
        // Recursively render children, excluding the current deck's branch
        const filteredChildren = deck.child_decks.filter(child => 
            !isDescendant(child, currentDeckId)
        );
        
        if (filteredChildren.length > 0) {
            html += renderDeckTree(filteredChildren, level + 1, currentDeckId);
        }
        
        html += '</li>';
    });
    
    html += '</ul>';
    return html;
}

function isDescendant(deck, ancestorId) {
    if (deck.flashcard_deck_id == ancestorId) return true;
    
    for (const child of deck.child_decks) {
        if (isDescendant(child, ancestorId)) return true;
    }
    
    return false;
}

async function handleMoveConfirm(deckId) {
    const button = document.getElementById('confirmMoveBtn');
    const normalState = button.querySelector('.normal-state');
    const loadingState = button.querySelector('.loading-state');
    const statusDiv = document.getElementById('moveStatus');
    
    // Determine new parent ID based on radio button selection
    const rootDeckOption = document.getElementById('rootDeck');
    const parentDeckSelect = document.getElementById('parentDeckSelect');
    
    let newParentId = null;
    
    if (!rootDeckOption.checked) {
        newParentId = parentDeckSelect.value;
    }
    
    button.disabled = true;
    normalState.classList.add('d-none');
    loadingState.classList.remove('d-none');
    
    try {
        const response = await fetch(`/deck/move/${deckId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                new_parent_id: newParentId
            }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="alert alert-success mt-3">
                    <i class="bi bi-check-circle-fill"></i> ${data.message}
                </div>
            `;
            setTimeout(() => location.reload(), 1000);
        } else {
            throw new Error(data.error || 'Failed to move deck');
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="alert alert-danger mt-3">
                <i class="bi bi-exclamation-circle-fill"></i> ${error.message}
            </div>
        `;
        button.disabled = false;
        normalState.classList.remove('d-none');
        loadingState.classList.add('d-none');
    }
}

// Add this new function to load due counts
async function loadDueCounts() {
    try {
        const response = await fetch('/deck/api/due-counts');
        if (!response.ok) {
            throw new Error('Failed to load due counts');
        }
        
        const dueCounts = await response.json();
        
        // Update all due today menu items
        const dueItems = document.querySelectorAll('.due-today-item');
        dueItems.forEach(item => {
            const deckId = item.dataset.deckId;
            const dueCount = dueCounts[deckId] || 0;
            
            // Update the badge
            const badge = item.querySelector('.due-badge');
            if (badge) {
                badge.textContent = dueCount;
            }
            
            // Disable the link if there are no due cards
            if (dueCount === 0) {
                item.classList.add('disabled');
                item.setAttribute('aria-disabled', 'true');
                if (item.tagName === 'A') {
                    item.href = 'javascript:void(0)';
                }
            } else {
                item.classList.remove('disabled');
                item.removeAttribute('aria-disabled');
            }
        });
    } catch (error) {
        console.error('Error loading due counts:', error);
    }
}
