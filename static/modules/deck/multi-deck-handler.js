/**
 * Handles functionality for creating multiple decks at once
 */
export function initializeMultiDeckUI() {
    setupEmptyDeckModal();
    setupSubDeckModal();
}

function setupEmptyDeckModal() {
    const modal = document.getElementById('createEmptyDeckModal');
    if (!modal) return;
    
    const container = document.getElementById('deckInputsContainer');
    const addButton = document.getElementById('addMoreDecksBtn');
    const countLabel = document.getElementById('deckCountLabel');
    const form = document.getElementById('createEmptyDeckForm');
    
    let deckCount = 1;
    
    // Add deck input group when button is clicked
    addButton.addEventListener('click', () => {
        deckCount++;
        const newDeckGroup = createDeckInputGroup(deckCount, false);
        container.appendChild(newDeckGroup);
        updateDeckCounter(countLabel, deckCount);
    });
    
    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Show loading state
        const submitButton = form.querySelector('button[type="submit"]');
        showLoadingState(submitButton, true);
        
        // Show processing message
        const messagesContainer = document.getElementById('createEmptyDeckMessages');
        showMessage(messagesContainer, 'processing');
        
        // Collect all deck data
        const decks = collectDeckData(container);
        
        // Check if we have any valid decks
        if (decks.length === 0) {
            showMessage(messagesContainer, 'error', "Please provide at least one deck name");
            showLoadingState(submitButton, false);
            return;
        }
        
        try {
            // Send to backend - FIX: Add /deck prefix to the URL path
            const response = await fetch('/deck/create_empty', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ decks }),
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Show success message with count
                const message = `Successfully created ${decks.length} deck${decks.length > 1 ? 's' : ''}!`;
                showMessage(messagesContainer, 'success', message);
                
                // Redirect after a short delay to show the success message
                setTimeout(() => {
                    if (data.decks && data.decks.length > 0) {
                        window.location.href = `/deck/${data.decks[0].deck_id}`;
                    } else {
                        window.location.reload();
                    }
                }, 1500);
            } else {
                showMessage(messagesContainer, 'error', data.error || "Failed to create decks");
                showLoadingState(submitButton, false);
            }
        } catch (error) {
            showMessage(messagesContainer, 'error', "Network error, please try again");
            showLoadingState(submitButton, false);
        }
    });
}

function setupSubDeckModal() {
    const modal = document.getElementById('deckModal');
    if (!modal) return;
    
    const container = document.getElementById('subDeckInputsContainer');
    const addButton = document.getElementById('addMoreSubDecksBtn');
    const countLabel = document.getElementById('subDeckCountLabel');
    const form = document.getElementById('createDeckForm');
    
    let deckCount = 1;
    
    // Add deck input group when button is clicked
    if (addButton) {
        addButton.addEventListener('click', () => {
            deckCount++;
            const newDeckGroup = createDeckInputGroup(deckCount, true);
            container.appendChild(newDeckGroup);
            updateDeckCounter(countLabel, deckCount);
        });
    }
    
    // IMPORTANT: Only attach event listener if we're in multi-deck mode
    // Check if we have the add more button - if not, we're in single-deck mode
    // and the form will be handled by form-handlers.js
    if (form && addButton) {
        // We're in multi-deck mode, attach the handler
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Show loading state
            const submitButton = form.querySelector('button[type="submit"]');
            showLoadingState(submitButton, true);
            
            // Show processing message
            const messagesContainer = document.getElementById('createSubDeckMessages');
            showMessage(messagesContainer, 'processing');
            
            // Get parent deck ID
            const parentDeckId = form.querySelector('input[name="parent_deck_id"]').value;
            
            // Collect all deck data
            const decks = collectDeckData(container);
            
            // Check if we have any valid decks
            if (decks.length === 0) {
                showMessage(messagesContainer, 'error', "Please provide at least one deck name");
                showLoadingState(submitButton, false);
                return;
            }
            
            try {
                // Send to backend - FIX: Add /deck prefix to the URL path
                const response = await fetch('/deck/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        decks,
                        parent_deck_id: parentDeckId
                    }),
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Show success message with count
                    const message = `Successfully created ${decks.length} sub-deck${decks.length > 1 ? 's' : ''}!`;
                    showMessage(messagesContainer, 'success', message);
                    
                    // Reload page after a short delay to show the success message
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showMessage(messagesContainer, 'error', data.error || "Failed to create decks");
                    showLoadingState(submitButton, false);
                }
            } catch (error) {
                showMessage(messagesContainer, 'error', "Network error, please try again");
                showLoadingState(submitButton, false);
            }
        });
    }
}

/**
 * Create a new deck input group with remove button
 */
function createDeckInputGroup(index, isSubDeck) {
    const group = document.createElement('div');
    group.className = 'deck-input-group mb-3';
    
    // Create deck header with label and remove button
    const header = document.createElement('div');
    header.className = 'd-flex justify-content-between align-items-center mb-2';
    
    const label = document.createElement('label');
    label.className = 'form-label mb-0';
    label.textContent = isSubDeck ? `Sub-deck ${index}` : `Deck ${index}`;
    
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-sm btn-outline-danger px-2 py-0';
    removeBtn.innerHTML = '<i class="bi bi-x"></i>';
    removeBtn.addEventListener('click', () => {
        group.remove();
        // Update counter after removal
        const containerID = isSubDeck ? 'subDeckInputsContainer' : 'deckInputsContainer';
        const countLabelID = isSubDeck ? 'subDeckCountLabel' : 'deckCountLabel';
        const container = document.getElementById(containerID);
        const countLabel = document.getElementById(countLabelID);
        const newCount = container.querySelectorAll('.deck-input-group').length;
        updateDeckCounter(countLabel, newCount);
    });
    
    header.appendChild(label);
    header.appendChild(removeBtn);
    
    // Create input fields
    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.className = 'form-control mb-2 deck-name-input';
    nameInput.placeholder = 'Deck Name';
    nameInput.required = true;
    
    const descInput = document.createElement('textarea');
    descInput.className = 'form-control deck-description-input';
    descInput.placeholder = 'Description (optional)';
    descInput.rows = 2;
    
    // Assemble the group
    group.appendChild(header);
    group.appendChild(nameInput);
    group.appendChild(descInput);
    
    return group;
}

/**
 * Update the deck counter label
 */
function updateDeckCounter(countLabel, count) {
    if (countLabel) {
        countLabel.textContent = count === 1 ? '1 deck' : `${count} decks`;
    }
}

/**
 * Collect deck data from input fields
 */
function collectDeckData(container) {
    const decks = [];
    
    const deckGroups = container.querySelectorAll('.deck-input-group');
    deckGroups.forEach(group => {
        const nameInput = group.querySelector('.deck-name-input');
        const descInput = group.querySelector('.deck-description-input');
        
        if (nameInput && nameInput.value.trim()) {
            decks.push({
                name: nameInput.value.trim(),
                description: descInput ? descInput.value.trim() : ''
            });
        }
    });
    
    return decks;
}

/**
 * Show or hide loading state on submit button
 */
function showLoadingState(button, isLoading) {
    if (!button) return;
    
    const normalState = button.querySelector('.normal-state');
    const loadingState = button.querySelector('.loading-state');
    
    if (isLoading) {
        button.disabled = true;
        if (normalState) normalState.classList.add('d-none');
        if (loadingState) loadingState.classList.remove('d-none');
    } else {
        button.disabled = false;
        if (normalState) normalState.classList.remove('d-none');
        if (loadingState) normalState.classList.add('d-none');
    }
}

/**
 * Show error message in the form
 */
function showError(form, message) {
    const statusDiv = form.querySelector('#createEmptyDeckStatus') || 
                     form.querySelector('#createDeckStatus');
                     
    if (statusDiv) {
        statusDiv.innerHTML = `<div class="alert alert-danger">${message}</div>`;
    }
}

/**
 * Show a message in the messages container
 * @param {Element} container - The messages container element
 * @param {string} type - The message type: 'processing', 'success', or 'error'
 * @param {string} [message] - Optional custom message text for success/error
 */
function showMessage(container, type, message = null) {
    if (!container) return;
    
    // Show the container
    container.classList.remove('d-none');
    
    // Hide all message types
    container.querySelectorAll('.processing-message, .success-message, .error-message').forEach(el => {
        el.classList.add('d-none');
    });
    
    // Show the appropriate message
    const messageElement = container.querySelector(`.${type}-message`);
    if (messageElement) {
        messageElement.classList.remove('d-none');
        
        // Update message text if provided (for success/error)
        if (message && type !== 'processing') {
            const textElement = messageElement.querySelector('.message-text');
            if (textElement) textElement.textContent = message;
        }
        
        // If it's processing, count the number of decks
        if (type === 'processing') {
            // Fix: Get the deck groups from the correct container element
            // Find the container closest to this message container
            const emptyDeckContainer = document.getElementById('deckInputsContainer');
            const subDeckContainer = document.getElementById('subDeckInputsContainer');
            
            // Get count from the appropriate container
            let count = 0;
            if (container.id === 'createEmptyDeckMessages' && emptyDeckContainer) {
                count = emptyDeckContainer.querySelectorAll('.deck-input-group').length;
            } else if (container.id === 'createSubDeckMessages' && subDeckContainer) {
                count = subDeckContainer.querySelectorAll('.deck-input-group').length;
            }
            
            const textElement = messageElement.querySelector('div:last-child');
            if (textElement) {
                textElement.innerHTML = count > 1 ? 
                    `Creating ${count} decks<span class="dots">...</span>` : 
                    `Creating deck<span class="dots">...</span>`;
            }
        }
    }
}
