// Track if form handlers have been initialized to prevent duplicates
let formHandlersInitialized = false;

// Modify this file to include the multi-deck functionality import
import { initializeMultiDeckUI } from './multi-deck-handler.js';

export function initializeFormHandlers(modals = {}) {
    // Prevent duplicate initialization
    if (formHandlersInitialized) {
        console.log("Form handlers already initialized, skipping");
        return;
    }
    
    console.log("Initializing form handlers");

    const { deckModal, generateModal, emptyDeckModal } = modals;

    // Create deck form handler
    const createDeckForm = document.getElementById('createDeckForm');
    if (createDeckForm) {
        // Check if we're in multi-deck mode - if we are, let multi-deck-handler handle it
        const isMultiDeckMode = !!document.getElementById('addMoreSubDecksBtn');
        
        if (!isMultiDeckMode) {
            // Only attach handler if we're not in multi-deck mode
            // Remove any existing submit handlers
            createDeckForm.removeEventListener('submit', handleCreateSubdeckSubmit);
            createDeckForm.addEventListener('submit', function(e) {
                handleCreateSubdeckSubmit(e, deckModal);
            });
        }
    }

    // Generate flashcards form handler
    const generateForm = document.getElementById('generateForm');
    if (generateForm) {
        // Remove any existing submit handlers
        generateForm.removeEventListener('submit', handleGenerateSubmit);
        generateForm.addEventListener('submit', function(e) {
            handleGenerateSubmit(e, generateModal);
        });
    }

    // Initialize multi-deck UI
    initializeMultiDeckUI();

    // Mark as initialized
    formHandlersInitialized = true;

    // Form submission handlers
    async function handleCreateSubdeckSubmit(e, deckModalInstance) {
        e.preventDefault();
        const form = e.target;
        const submitButton = form.querySelector('button[type="submit"]');
        const normalState = submitButton.querySelector('.normal-state');
        const loadingState = submitButton.querySelector('.loading-state');
        
        // Show processing message in the new message container
        const messagesContainer = document.getElementById('createSubDeckMessages');
        if (messagesContainer) {
            messagesContainer.classList.remove('d-none');
            const processingMsg = messagesContainer.querySelector('.processing-message');
            const successMsg = messagesContainer.querySelector('.success-message');
            const errorMsg = messagesContainer.querySelector('.error-message');
            
            // Hide all messages and show processing
            if (processingMsg) processingMsg.classList.remove('d-none');
            if (successMsg) successMsg.classList.add('d-none');
            if (errorMsg) errorMsg.classList.add('d-none');
        }

        // Add debug log
        console.log("Single deck mode: handling subdeck form submission");

        submitButton.disabled = true;
        if (normalState && loadingState) {
            normalState.classList.add('d-none');
            loadingState.classList.remove('d-none');
        }

        try {
            // Fix: Convert form data to JSON payload
            const formData = new FormData(form);
            const jsonData = {
                name: formData.get('name'),
                description: formData.get('description'),
                parent_deck_id: formData.get('parent_deck_id')
            };

            const response = await fetch('/deck/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(jsonData)
            });
            
            if (response.ok) {
                // Show success message in new container
                if (messagesContainer) {
                    const processingMsg = messagesContainer.querySelector('.processing-message');
                    const successMsg = messagesContainer.querySelector('.success-message');
                    
                    if (processingMsg) processingMsg.classList.add('d-none');
                    if (successMsg) {
                        successMsg.classList.remove('d-none');
                        const textEl = successMsg.querySelector('.message-text');
                        if (textEl) textEl.textContent = 'Sub-deck created successfully!';
                    }
                }
                
                setTimeout(() => {
                    if (deckModalInstance) deckModalInstance.hide();
                    location.reload();
                }, 1000);
            } else {
                throw new Error('Failed to create sub-deck');
            }
        } catch (error) {
            console.error('Error creating deck:', error);
            
            // Show error message in new container
            if (messagesContainer) {
                const processingMsg = messagesContainer.querySelector('.processing-message');
                const errorMsg = messagesContainer.querySelector('.error-message');
                
                if (processingMsg) processingMsg.classList.add('d-none');
                if (errorMsg) {
                    errorMsg.classList.remove('d-none');
                    const textEl = errorMsg.querySelector('.message-text');
                    if (textEl) textEl.textContent = 'Failed to create sub-deck. Please try again.';
                }
            }
            
            submitButton.disabled = false;
            if (normalState && loadingState) {
                normalState.classList.remove('d-none');
                loadingState.classList.add('d-none');
            }
        }
    }

    async function handleGenerateSubmit(e, generateModalInstance) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        const submitButton = form.querySelector('button[type="submit"]');
        const normalState = submitButton.querySelector('.normal-state');
        const loadingState = submitButton.querySelector('.loading-state');
        const statusDiv = form.querySelector('#generateStatus');

        submitButton.disabled = true;
        if (normalState && loadingState) {
            normalState.classList.add('d-none');
            loadingState.classList.remove('d-none');
        }
        
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> Generating flashcards... This may take a minute.
                </div>
            `;
        }

        try {
            const action = form.getAttribute('action') || '/flashcard/generate-flashcards';
            const response = await fetch(action, {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // Check if response is JSON
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    const data = await response.json();
                    if (statusDiv) {
                        statusDiv.innerHTML = `
                            <div class="alert alert-success">
                                <i class="bi bi-check-circle"></i> Flashcards generated successfully!
                            </div>
                        `;
                    }
                    setTimeout(() => {
                        if (generateModalInstance) generateModalInstance.hide();
                        window.location.href = data.redirect_url || window.location.href;
                    }, 1000);
                } else {
                    // Handle HTML response (direct page load)
                    window.location.href = response.url;
                }
            } else {
                throw new Error('Failed to generate cards');
            }
        } catch (error) {
            console.error('Error generating cards:', error);
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle"></i> Failed to generate cards. Please try again.
                    </div>
                `;
            }
        } finally {
            submitButton.disabled = false;
            if (normalState && loadingState) {
                normalState.classList.remove('d-none');
                loadingState.classList.add('d-none');
            }
        }
    }
}
