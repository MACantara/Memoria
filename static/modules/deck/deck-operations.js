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
    let deckToMoveId = null;
    const moveModal = new bootstrap.Modal(document.getElementById('moveDeckModal'));
    
    window.showMoveDeckModal = async (deckId, deckName) => {
        deckToMoveId = deckId;
        document.getElementById('deckToMoveName').textContent = deckName;
        document.getElementById('moveStatus').innerHTML = '';
        
        // Load the deck tree
        await loadDeckTree(deckId);
        
        moveModal.show();
    };
    
    document.getElementById('confirmMoveBtn')?.addEventListener('click', async () => {
        handleMoveConfirm(deckToMoveId);
    });
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
    
    // Get selected destination
    const selectedRadio = document.querySelector('input[name="destinationDeck"]:checked');
    if (!selectedRadio) {
        statusDiv.innerHTML = `
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle"></i> Please select a destination
            </div>
        `;
        return;
    }
    
    const newParentId = selectedRadio.value || null;  // Empty string means root level
    
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
                new_parent_id: newParentId === '' ? null : newParentId
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i> ${data.message}
                </div>
            `;
            setTimeout(() => location.reload(), 1000);
        } else {
            throw new Error(data.error || 'Failed to move deck');
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
