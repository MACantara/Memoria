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
        
        try {
            const response = await fetch('/generate', {
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
                window.location.href = data.redirect_url;
            }
        } catch (error) {
            console.error('Error generating flashcards:', error);
            this.form.submit();
        }
    }
}
