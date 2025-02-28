export function initializeFormHandlers(modals = {}) {
    const { deckModal, generateModal, emptyDeckModal } = modals;

    // Create deck form handler
    document.getElementById('createDeckForm')?.addEventListener('submit', async (e) => {
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
    });

    // Empty deck form handler
    document.getElementById('createEmptyDeckForm')?.addEventListener('submit', async (e) => {
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
    });

    // Generate cards form handler
    const generateForms = document.querySelectorAll('#generateForm');
    generateForms.forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const submitButton = e.target.querySelector('button[type="submit"]');
            const normalState = submitButton.querySelector('.normal-state');
            const loadingState = submitButton.querySelector('.loading-state');
            const statusDiv = e.target.querySelector('#generateStatus');
            
            submitButton.disabled = true;
            normalState.classList.add('d-none');
            loadingState.classList.remove('d-none');
            
            // Clear previous status
            statusDiv.innerHTML = '';
            
            try {
                // Submit the form and start generation process
                const action = form.getAttribute('action');
                console.log(`Submitting to: ${action}`);
                
                const response = await fetch(action, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Request failed with status ${response.status}: ${errorText || 'Unknown error'}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    // Redirect to progress tracking page
                    const progressUrl = `/flashcard/generation/generation-status?job_id=${data.job_id}&deck_id=${data.deck_id}`;
                    window.location.href = progressUrl;
                } else {
                    throw new Error(data.error || 'Failed to generate cards');
                }
            } catch (error) {
                console.error('Error starting generation:', error);
                statusDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle"></i> ${error.message || 'Failed to generate cards. Please try again.'}
                    </div>
                `;
                
                // Reset button
                submitButton.disabled = false;
                normalState.classList.remove('d-none');
                loadingState.classList.add('d-none');
            }
        });
    });
}
