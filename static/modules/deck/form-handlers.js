// Track if form handlers have been initialized to prevent duplicates
let formHandlersInitialized = false;

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
        // Remove any existing submit handlers
        createDeckForm.removeEventListener('submit', handleCreateSubdeckSubmit);
        createDeckForm.addEventListener('submit', handleCreateSubdeckSubmit);
    }

    // Create empty deck form handler
    const createEmptyDeckForm = document.getElementById('createEmptyDeckForm');
    if (createEmptyDeckForm) {
        // Remove any existing submit handlers
        createEmptyDeckForm.removeEventListener('submit', handleCreateEmptyDeckSubmit);
        createEmptyDeckForm.addEventListener('submit', handleCreateEmptyDeckSubmit);
    }

    // Generate flashcards form handler
    const generateForm = document.getElementById('generateForm');
    if (generateForm) {
        // Remove any existing submit handlers
        generateForm.removeEventListener('submit', handleGenerateSubmit);
        generateForm.addEventListener('submit', handleGenerateSubmit);
    }

    // Mark as initialized
    formHandlersInitialized = true;

    // Form submission handlers
    function handleCreateSubdeckSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const submitButton = form.querySelector('button[type="submit"]');
        const normalState = submitButton.querySelector('.normal-state');
        const loadingState = submitButton.querySelector('.loading-state');
        const statusDiv = document.getElementById('createDeckStatus');

        submitButton.disabled = true;
        normalState.classList.add('d-none');
        loadingState.classList.remove('d-none');

        try {
            const response = await fetch('/deck/create', {
                method: 'POST',
                body: new FormData(form)
            });
            
            if (response.ok) {
                statusDiv.innerHTML = `
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle"></i> Sub-deck created successfully!
                    </div>
                `;
                setTimeout(() => {
                    deckModal?.hide();
                    location.reload();
                }, 1000);
            } else {
                throw new Error('Failed to create sub-deck');
            }
        } catch (error) {
            console.error('Error creating deck:', error);
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Failed to create sub-deck. Please try again.
                </div>
            `;
            submitButton.disabled = false;
            normalState.classList.remove('d-none');
            loadingState.classList.add('d-none');
        }
    }

    function handleCreateEmptyDeckSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const submitButton = form.querySelector('button[type="submit"]');
        const normalState = submitButton.querySelector('.normal-state');
        const loadingState = submitButton.querySelector('.loading-state');
        const statusDiv = document.getElementById('createEmptyDeckStatus');

        submitButton.disabled = true;
        normalState.classList.add('d-none');
        loadingState.classList.remove('d-none');
        
        try {
            const response = await fetch('/deck/create_empty', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: document.getElementById('emptyDeckName').value,
                    description: document.getElementById('emptyDeckDescription').value
                })
            });
            
            if (response.ok) {
                statusDiv.innerHTML = `
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle"></i> Deck created successfully!
                    </div>
                `;
                setTimeout(() => {
                    emptyDeckModal?.hide();
                    location.reload();
                }, 1000);
            } else {
                throw new Error('Failed to create deck');
            }
        } catch (error) {
            console.error('Error creating deck:', error);
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Failed to create deck. Please try again.
                </div>
            `;
            submitButton.disabled = false;
            normalState.classList.remove('d-none');
            loadingState.classList.add('d-none');
        }
    }

    function handleGenerateSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(e.target);
        const submitButton = e.target.querySelector('button[type="submit"]');
        const normalState = submitButton.querySelector('.normal-state');
        const loadingState = submitButton.querySelector('.loading-state');
        const statusDiv = e.target.querySelector('#generateStatus');

        submitButton.disabled = true;
        normalState.classList.add('d-none');
        loadingState.classList.remove('d-none');
        statusDiv.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i> Generating flashcards... This may take a minute.
            </div>
        `;

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
                    statusDiv.innerHTML = `
                        <div class="alert alert-success">
                            <i class="bi bi-check-circle"></i> Flashcards generated successfully!
                        </div>
                    `;
                    setTimeout(() => {
                        generateModal?.hide();
                        window.location.href = data.redirect_url || location.reload();
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
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Failed to generate cards. Please try again.
                </div>
            `;
        } finally {
            submitButton.disabled = false;
            normalState.classList.remove('d-none');
            loadingState.classList.add('d-none');
        }
    }
}
