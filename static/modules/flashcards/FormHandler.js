export class FormHandler {
    constructor() {
        this.form = document.getElementById('generateForm');
        this.initializeForm();
    }

    initializeForm() {
        if (!this.form) return;

        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleSubmit(e);
        });
    }

    async handleSubmit(e) {
        const formData = new FormData(this.form);
        const submitButton = this.form.querySelector('button[type="submit"]');
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
            const response = await fetch('/generate-flashcards', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.success) {
                statusDiv.innerHTML = `
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle"></i> Flashcards generated successfully!
                    </div>
                `;
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 1000);
            }
        } catch (error) {
            console.error('Error generating flashcards:', error);
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Failed to generate flashcards. Please try again.
                </div>
            `;
            this.form.submit();
        } finally {
            submitButton.disabled = false;
            normalState.classList.remove('d-none');
            loadingState.classList.add('d-none');
        }
    }
}
