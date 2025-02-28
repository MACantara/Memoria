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
            const streamProgressDiv = document.getElementById('streamProgress');
            const progressBar = document.querySelector('#streamProgress .progress-bar');
            const cardsGeneratedSpan = document.getElementById('cardsGenerated');
            const previewCardsDiv = document.getElementById('previewCards');
            
            // Check if browser supports EventSource
            const supportsStreaming = 'EventSource' in window;
            
            submitButton.disabled = true;
            normalState.classList.add('d-none');
            loadingState.classList.remove('d-none');
            
            // Clear previous status and preview
            statusDiv.innerHTML = '';
            previewCardsDiv.innerHTML = '<p class="text-muted text-center small">Cards will appear as they\'re generated</p>';
            
            if (supportsStreaming) {
                // Use streaming approach
                streamProgressDiv.classList.remove('d-none');
                statusDiv.innerHTML = `
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle"></i> Generating flashcards in real-time...
                    </div>
                `;
                
                // Get form data
                const parentDeckId = formData.get('parent_deck_id');
                const topic = formData.get('topic');
                const batchSize = formData.get('batch_size');
                
                try {
                    // Create the EventSource with proper URL for GET request
                    const baseUrl = form.getAttribute('action') || '/flashcard/generate-flashcards';
                    const streamUrl = new URL(baseUrl, window.location.origin);
                    
                    // Add parameters as query string for GET request
                    streamUrl.searchParams.append('parent_deck_id', parentDeckId);
                    streamUrl.searchParams.append('topic', topic);
                    streamUrl.searchParams.append('batch_size', batchSize);
                    
                    console.log('Creating EventSource with URL:', streamUrl.toString());
                    const eventSource = new EventSource(streamUrl.toString());
                    
                    // Set up event handlers for EventSource
                    eventSource.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            
                            switch(data.type) {
                                case 'deck_created':
                                    console.log('Deck created:', data);
                                    break;
                                    
                                case 'progress':
                                    // Update progress bar
                                    progressBar.style.width = `${data.percentage}%`;
                                    progressBar.setAttribute('aria-valuenow', data.percentage);
                                    cardsGeneratedSpan.textContent = data.count;
                                    break;
                                    
                                case 'card':
                                    // Add card preview
                                    const cardElement = document.createElement('div');
                                    cardElement.className = 'mb-2 border-bottom pb-1';
                                    cardElement.innerHTML = `
                                        <div><strong>Q:</strong> ${data.question}</div>
                                        <div><strong>A:</strong> ${data.correct}</div>
                                    `;
                                    previewCardsDiv.appendChild(cardElement);
                                    // Scroll to bottom to show latest card
                                    previewCardsDiv.scrollTop = previewCardsDiv.scrollHeight;
                                    break;
                                    
                                case 'complete':
                                    // Generation complete
                                    eventSource.close();
                                    statusDiv.innerHTML = `
                                        <div class="alert alert-success">
                                            <i class="bi bi-check-circle"></i> Successfully generated ${data.count} flashcards!
                                        </div>
                                    `;
                                    
                                    // Complete the progress bar
                                    progressBar.style.width = '100%';
                                    progressBar.setAttribute('aria-valuenow', 100);
                                    progressBar.classList.remove('progress-bar-animated');
                                    
                                    // Redirect after a short delay
                                    setTimeout(() => {
                                        window.location.href = data.redirect_url;
                                    }, 1500);
                                    break;
                                    
                                case 'error':
                                    // Handle error
                                    eventSource.close();
                                    throw new Error(data.message);
                                    break;
                            }
                        } catch (error) {
                            console.error('Error processing stream event:', error);
                            statusDiv.innerHTML = `
                                <div class="alert alert-danger">
                                    <i class="bi bi-exclamation-triangle"></i> Error: ${error.message}
                                </div>
                            `;
                            eventSource.close();
                            submitButton.disabled = false;
                            normalState.classList.remove('d-none');
                            loadingState.classList.add('d-none');
                        }
                    };
                    
                    eventSource.onerror = (error) => {
                        console.error('EventSource error:', error);
                        eventSource.close();
                        statusDiv.innerHTML = `
                            <div class="alert alert-danger">
                                <i class="bi bi-exclamation-triangle"></i> Connection lost. Please try again.
                            </div>
                        `;
                        submitButton.disabled = false;
                        normalState.classList.remove('d-none');
                        loadingState.classList.add('d-none');
                    };
                } catch (error) {
                    console.error('Error setting up EventSource:', error);
                    statusDiv.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="bi bi-exclamation-triangle"></i> Error: ${error.message}
                        </div>
                    `;
                    submitButton.disabled = false;
                    normalState.classList.remove('d-none');
                    loadingState.classList.add('d-none');
                }
            } else {
                // Fall back to traditional approach
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
                                const generateModal = document.getElementById('generateModal');
                                const bootstrapModal = bootstrap.Modal.getInstance(generateModal);
                                if (bootstrapModal) {
                                    bootstrapModal.hide();
                                }
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
        });
    });
}
