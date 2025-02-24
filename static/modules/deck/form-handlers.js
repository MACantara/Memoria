export function initializeFormHandlers(deckModal, generateModal) {
    document.getElementById('createDeckForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const submitButton = e.target.querySelector('button[type="submit"]');
        submitButton.disabled = true;

        try {
            const response = await fetch('/deck/create', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                deckModal.hide();
                location.reload();
            } else {
                throw new Error('Failed to create deck');
            }
        } catch (error) {
            console.error('Error creating deck:', error);
            alert('Failed to create deck. Please try again.');
        } finally {
            submitButton.disabled = false;
        }
    });

    document.getElementById('generateForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const submitButton = e.target.querySelector('button[type="submit"]');
        const normalState = submitButton.querySelector('.normal-state');
        const loadingState = submitButton.querySelector('.loading-state');
        const statusDiv = document.getElementById('generateStatus');

        submitButton.disabled = true;
        normalState.classList.add('d-none');
        loadingState.classList.remove('d-none');
        statusDiv.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i> Generating flashcards... This may take a minute.
            </div>
        `;

        try {
            const response = await fetch('/generate_for_deck', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                statusDiv.innerHTML = `
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle"></i> Flashcards generated successfully!
                    </div>
                `;
                setTimeout(() => {
                    generateModal.hide();
                    location.reload();
                }, 1000);
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
    });
}
